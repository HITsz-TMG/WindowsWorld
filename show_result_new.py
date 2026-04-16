#!/usr/bin/env python3
import os
import re
import json
import shutil
import statistics
from collections import defaultdict


def parse_scores_from_text(text):
    # 尝试直接匹配 "Intermediate Score: x, Final Result: y"
    m = re.search(r'Intermediate Score:\s*([0-9+\-\.eE]+)\s*,\s*Final Result:\s*([0-9+\-\.eE]+)', text)
    if m:
        try:
            inter = float(m.group(1))
            final = float(m.group(2))
            return inter, final
        except Exception:
            pass
    # 宽松匹配：分别找 Intermediate 和 Final 的数字
    m1 = re.search(r'Intermediate Score:\s*([0-9+\-\.eE]+)', text)
    m2 = re.search(r'Final Result:\s*([0-9+\-\.eE]+)', text)
    if m1 and m2:
        try:
            return float(m1.group(1)), float(m2.group(1))
        except Exception:
            return None
    # 寻找任意两个数字作为兜底（不建议常用）
    nums = re.findall(r'([0-9]+(?:\.[0-9]+)?)', text)
    if len(nums) >= 2:
        return float(nums[0]), float(nums[1])
    return None


def stats(values):
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
    }


def classify(task_name):
    name = task_name.lower()
    if 'l1' in name:
        return 'l1'
    if 'l2' in name:
        return 'l2'
    if 'l3' in name:
        return 'l3'
    if 'l4' in name:
        return 'l4'
    return 'other'


def aggregate(hf_result_root='hf_result'):
    root = os.path.abspath(hf_result_root)
    if not os.path.isdir(root):
        print(f'目录不存在: {root}')
        return

    categories = defaultdict(lambda: {"inter": [], "final": [], "tasks": [], "steps": [], "total_time": [], "avg_per_step": []})

    for task in sorted(os.listdir(root)):
        task_path = os.path.join(root, task)
        if not os.path.isdir(task_path):
            continue

        # 查找时间戳命名的子文件夹，优先最新（按名字排序）
        subdirs = [d for d in os.listdir(task_path) if os.path.isdir(os.path.join(task_path, d))]
        found = False
        for sd in sorted(subdirs, reverse=True):
            candidate = os.path.join(task_path, sd, 'result.json')
            if os.path.isfile(candidate):
                with open(candidate, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        line2 = lines[1].strip()
                        parsed = parse_scores_from_text(line2)
                        if not parsed:
                            # 如果第二行解析失败，尝试全文解析
                            f.seek(0)
                            full = f.read()
                            parsed = parse_scores_from_text(full)
                    else:
                        f.seek(0)
                        full = f.read()
                        parsed = parse_scores_from_text(full)

                if parsed:
                    inter, final = parsed
                    cat = classify(task)
                    categories[cat]["inter"].append(inter)
                    categories[cat]["final"].append(final)
                    categories[cat]["tasks"].append(task)
                else:
                    # 无法解析则跳过
                    pass
                # 同目录下尝试读取 traj.jsonl，统计步数和耗时
                traj_path = os.path.join(task_path, sd, 'traj.jsonl')
                if os.path.isfile(traj_path):
                    try:
                        max_step = -1
                        total_predict = 0.0
                        with open(traj_path, 'r', encoding='utf-8', errors='ignore') as tf:
                            for line in tf:
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    obj = json.loads(line)
                                except Exception:
                                    # 如果不是严格的 JSON 行，跳过
                                    continue
                                # 支持多种字段名
                                step_num = obj.get('step_num') if isinstance(obj, dict) else None
                                if step_num is None:
                                    step_num = obj.get('step') if isinstance(obj, dict) else None
                                try:
                                    if isinstance(step_num, (int, float)):
                                        max_step = max(max_step, int(step_num))
                                except Exception:
                                    pass

                                predict_time = obj.get('predict_time') if isinstance(obj, dict) else None
                                if predict_time is None:
                                    predict_time = obj.get('predictTime') if isinstance(obj, dict) else None
                                try:
                                    if predict_time is not None:
                                        total_predict += float(predict_time)
                                except Exception:
                                    pass

                        used_steps = (max_step + 1) if max_step >= 0 else 0
                        avg_per_step = (total_predict / used_steps) if used_steps > 0 else None
                        # 将任务的步数和时间统计加入分类汇总
                        categories[cat]["steps"].append(used_steps)
                        categories[cat]["total_time"].append(total_predict)
                        if avg_per_step is not None:
                            categories[cat]["avg_per_step"].append(avg_per_step)
                    except Exception:
                        pass
                found = True
                break
        if not found:
            # 没有找到 result.json
            pass

    # 新增：计算 L1, L2, L3 成功任务的平均步数与基线之差
    successful_steps = defaultdict(list)
    for cat, data in categories.items():
        if cat in ['l1', 'l2', 'l3', 'l4']:
            final_scores = data.get("final", [])
            if cat == 'l4':
                final_scores = max(final_scores, data.get("inter", []))
            steps_list = data.get("steps", [])
            # 确保分数和步数列表长度一致
            for i in range(min(len(final_scores), len(steps_list))):
                if final_scores[i] == 1.0:
                    successful_steps[cat].append(steps_list[i])

    # 计算并展示统计
    report = {}
    # 用于计算整体均值
    all_inter_scores = []  # Intermediate（排除 l4/other）
    all_final_scores = []  # Final（所有任务）
    all_avg_per_step = []  # 所有任务的单步平均时间

    for cat, data in categories.items():
        inter_stats = stats(data["inter"])
        final_stats = stats(data["final"])

        # 收集整体分数
        # Intermediate 排除 l4 类任务（l4 在 classify 里会返回 'other'，这里排除含 l4 的）
        if cat != 'l4':
            all_inter_scores.extend(data["inter"])
        all_final_scores.extend(data["final"])

        # 收集所有任务的单步平均时间
        all_avg_per_step.extend(data.get('avg_per_step', []))

        # 格式化为百分比（乘以100，保留两位小数）
        def fmt_stat_percent(s):
            if s is None:
                return None
            out = s.copy()
            if out.get('mean') is not None:
                out['mean'] = round(out['mean'] * 100, 2)
            if out.get('median') is not None:
                out['median'] = round(out['median'] * 100, 2)
            if out.get('min') is not None:
                out['min'] = round(out['min'] * 100, 2)
            if out.get('max') is not None:
                out['max'] = round(out['max'] * 100, 2)
            return out

        steps_stats = None
        steps_list = data.get('steps', [])
        if steps_list:
            steps_stats = {
                'count': len(steps_list),
                'min': min(steps_list),
                'max': max(steps_list),
                'median': statistics.median(steps_list),
            }

        total_time_sum = sum(data.get('total_time', []))

        avg_per_step_stats = None
        avg_list = data.get('avg_per_step', [])
        if avg_list:
            avg_per_step_stats = {
                'count': len(avg_list),
                'min': min(avg_list),
                'max': max(avg_list),
                'mean': statistics.mean(avg_list),
                'median': statistics.median(avg_list),
            }

        # 对 avg_per_step 的 median 和 min/max 可以保留原值，打印时格式化
        report[cat] = {
            "task_count": len(set(data["tasks"])),
            "intermediate": fmt_stat_percent(inter_stats),
            "final": fmt_stat_percent(final_stats),
            "steps": steps_stats,
            "total_time_sum": total_time_sum,
            "avg_per_step": avg_per_step_stats,
        }

    # 计算整体均值
    overall_inter_avg = round(statistics.mean(all_inter_scores) * 100, 2) if all_inter_scores else None
    overall_final_avg = round(statistics.mean(all_final_scores) * 100, 2) if all_final_scores else None
    overall_avg_per_step = round(statistics.mean(all_avg_per_step), 4) if all_avg_per_step else None

    # 打印友好表格
    print('=' * 60)
    print('分类统计结果（分数以百分比显示）')
    print('=' * 60)
    for cat in sorted(report.keys()):
        r = report[cat]
        print(f'\n类别: {cat.upper()} — 任务数量: {r["task_count"]}')
        inter = r.get('intermediate')
        if inter:
            print(f'  中间分数: count={inter["count"]} min={inter["min"]:.2f}% max={inter["max"]:.2f}% mean={inter["mean"]:.2f}% median={inter["median"]:.2f}%')
        final = r.get('final')
        if final:
            print(f'  最终分数: count={final["count"]} min={final["min"]:.2f}% max={final["max"]:.2f}% mean={final["mean"]:.2f}% median={final["median"]:.2f}%')

        steps = r.get('steps')
        if steps:
            print(f'  步数(每任务): count={steps["count"]} min={steps["min"]} max={steps["max"]} median={round(steps["median"], 2)}')

        avgps = r.get('avg_per_step')
        if avgps:
            print(f'  平均每步耗时: count={avgps["count"]} min={round(avgps["min"], 4)}s max={round(avgps["max"], 4)}s mean={round(avgps["mean"], 4)}s median={round(avgps["median"], 4)}s')

    # 打印整体均值汇总
    print('\n' + '=' * 60)
    print('整体均值汇总')
    print('=' * 60)
    total_task_count = sum(r["task_count"] for r in report.values())
    inter_task_count = sum(r["task_count"] for cat, r in report.items() if cat not in ['l4', 'other'])
    print(f'总任务数: {total_task_count}')
    if overall_inter_avg is not None:
        print(f'Intermediate Score 均值 (排除L4, 共{inter_task_count}个任务): {overall_inter_avg:.2f}%')
    if overall_final_avg is not None:
        print(f'Final Score 均值 (所有任务, 共{total_task_count}个任务): {overall_final_avg:.2f}%')
    if overall_avg_per_step is not None:
        print(f'所有任务单步平均耗时: {overall_avg_per_step:.4f}s')
    print('')

    # 打印汇总表格
    print('=' * 90)
    print('汇总表格')
    print('=' * 90)
    
    # 获取各级别的 intermediate mean 和 final mean
    def get_mean(cat_key, score_type):
        if cat_key in report and report[cat_key].get(score_type):
            val = report[cat_key][score_type].get('mean')
            if val is not None:
                return f'{val:.2f}%'
        return '-'
    
    # 表头
    print('+' + '-' * 88 + '+')
    print('|{:^44}|{:^32}|{:^10}|'.format('Intermediate', 'Final', 'Mean Time'))
    print('+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+')
    print('|{:^10}|{:^10}|{:^10}|{:^10}|{:^10}|{:^10}|{:^10}|{:^10}|{:^10}|'.format(
        'L1', 'L2', 'L3', 'Avg', 'L1', 'L2', 'L3', 'L4', 'Avg'))
    print('+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+')
    
    # 数据行
    inter_l1 = get_mean('l1', 'intermediate')
    inter_l2 = get_mean('l2', 'intermediate')
    inter_l3 = get_mean('l3', 'intermediate')
    inter_avg = f'{overall_inter_avg:.2f}%' if overall_inter_avg is not None else '-'
    
    final_l1 = get_mean('l1', 'final')
    final_l2 = get_mean('l2', 'final')
    final_l3 = get_mean('l3', 'final')
    final_l4 = get_mean('l4', 'final')
    final_avg = f'{overall_final_avg:.2f}%' if overall_final_avg is not None else '-'
    
    avg_time = f'{overall_avg_per_step:.2f}s' if overall_avg_per_step is not None else '-'
    
    print('|{:^10}|{:^10}|{:^10}|{:^10}|{:^10}|{:^10}|{:^10}|{:^10}|{:^10}|'.format(
        inter_l1, inter_l2, inter_l3, inter_avg, final_l1, final_l2, final_l3, final_l4, final_avg))
    print('+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+' + '-' * 10 + '+')
    print(f'Mean Time (所有任务单步平均耗时): {avg_time}')
    print('')

    # 打印成功任务步数与基线的差异
    print('=' * 60)
    print('成功任务平均步数与基线差异')
    print('=' * 60)
    baselines = {'l1': 16, 'l2': 26, 'l3': 41, 'l4': 21}
    step_diffs = {}  # 保存步数差异用于 JSON 输出
    for cat in sorted(baselines.keys()):
        steps = successful_steps.get(cat)
        if steps:
            avg_steps = statistics.mean(steps)
            diff = avg_steps - baselines[cat]
            step_diffs[cat] = round(diff, 2)
            print(f'L{cat[1]} 级: 平均步数 {avg_steps:.2f}, 与基线 {baselines[cat]} 的差值为 {diff:.2f}')
        else:
            step_diffs[cat] = None
            print(f'L{cat[1]} 级: 没有成功的任务 (Final Result = 1.0)')
    print('')


    # 同时保存为 JSON 文件
    report['_overall'] = {
        'total_task_count': total_task_count,
        'intermediate_avg_percent': overall_inter_avg,
        'intermediate_task_count': inter_task_count,
        'final_avg_percent': overall_final_avg,
        'avg_per_step_all_tasks': overall_avg_per_step,
        'step_diffs': step_diffs,  # 新增: 成功任务步数与基线差异
    }
    out_path = os.path.join(root, 'summary_report.json')
    with open(out_path, 'w', encoding='utf-8') as fo:
        json.dump(report, fo, ensure_ascii=False, indent=2)
    print(f'已将汇总保存到: {out_path}')


def extract_results(hf_result_root='hf_result', out_dir='hf_result_json'):
    root = os.path.abspath(hf_result_root)
    dest = os.path.abspath(out_dir)
    if not os.path.isdir(root):
        print(f'来源目录不存在: {root}')
        return
    os.makedirs(dest, exist_ok=True)

    copied = 0
    skipped = 0
    not_found = []
    for task in sorted(os.listdir(root)):
        task_path = os.path.join(root, task)
        if not os.path.isdir(task_path):
            continue

        # 在任务目录下寻找子文件夹里的 result.json（优先最新的子文件夹）
        subdirs = [d for d in os.listdir(task_path) if os.path.isdir(os.path.join(task_path, d))]
        found = False
        for sd in sorted(subdirs, reverse=True):
            candidate = os.path.join(task_path, sd, 'result.json')
            if os.path.isfile(candidate):
                target_name = f"{task}.json"
                target_path = os.path.join(dest, target_name)
                try:
                    shutil.copyfile(candidate, target_path)
                    copied += 1
                except Exception as e:
                    print(f'复制失败: {candidate} -> {target_path}: {e}')
                found = True
                break
        if not found:
            not_found.append(task)
            skipped += 1

    print(f'已复制 {copied} 个 result.json 到: {dest}，跳过 {skipped} 个任务（未找到 result.json）')
    print(f'未找到的任务: {not_found}')
    # delete not_found
    for task in not_found:
        task_path = os.path.join(root, task)
        if os.path.isdir(task_path):
            try:
                shutil.rmtree(task_path)
                print(f'已删除无结果任务目录: {task_path}')
            except Exception as e:
                print(f'删除任务目录失败: {task_path}: {e}')


def batch_process_result_cache(result_cache_root='result_cache'):
    """
    批量处理 result_cache 目录下的所有实验结果。
    
    支持两种目录结构:
    
    结构1 (带 hf_result 子目录):
    result_cache/
    └── experiment_name/
        └── hf_result/
            └── task_id/
                └── timestamp/
                    └── result.json
    
    结构2 (直接放任务目录):
    result_cache/
    └── experiment_name/
        └── task_id/
            └── timestamp/
                └── result.json
    
    输出:
    - 每个实验的统计结果打印到控制台
    - 每个实验的 summary_report.json 保存到对应目录
    - 生成总览文件 result_cache/batch_summary.json
    """
    root = os.path.abspath(result_cache_root)
    if not os.path.isdir(root):
        print(f'result_cache 目录不存在: {root}')
        return
    
    # 获取所有实验目录
    experiment_dirs = []
    for item in sorted(os.listdir(root)):
        item_path = os.path.join(root, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            experiment_dirs.append(item)
    
    if not experiment_dirs:
        print(f'result_cache 目录下没有找到实验目录: {root}')
        return
    
    print('=' * 80)
    print(f'批量处理 result_cache 下的 {len(experiment_dirs)} 个实验')
    print('=' * 80)
    
    batch_summary = {}
    
    for exp_name in experiment_dirs:
        exp_path = os.path.join(root, exp_name)
        
        print(f'\n{"#" * 80}')
        print(f'# 实验: {exp_name}')
        print(f'{"#" * 80}')
        
        # 确定实际的结果目录：检查是否有 hf_result 子目录
        hf_result_path = os.path.join(exp_path, 'hf_result')
        if os.path.isdir(hf_result_path):
            # 结构1: experiment/hf_result/task_id/...
            result_root = hf_result_path
            print(f'  [检测到] hf_result 子目录结构')
        else:
            # 结构2: experiment/task_id/...
            result_root = exp_path
            print(f'  [检测到] 直接任务目录结构')
        
        # 检查是否有任务结果（排除 summary_report.json 等文件）
        task_dirs = [d for d in os.listdir(result_root) 
                     if os.path.isdir(os.path.join(result_root, d)) 
                     and not d.startswith('.') 
                     and d not in ['hf_result_json']]
        
        if not task_dirs:
            print(f'  [跳过] 没有找到任务结果目录')
            batch_summary[exp_name] = {'status': 'empty', 'task_count': 0}
            continue
        
        # 使用 aggregate 函数处理该实验目录
        try:
            aggregate(hf_result_root=result_root)
            
            # 读取生成的 summary_report.json
            summary_path = os.path.join(result_root, 'summary_report.json')
            if os.path.isfile(summary_path):
                with open(summary_path, 'r', encoding='utf-8') as f:
                    summary_data = json.load(f)
                batch_summary[exp_name] = {
                    'status': 'success',
                    'summary': summary_data
                }
            else:
                batch_summary[exp_name] = {'status': 'no_summary', 'task_count': len(task_dirs)}
                
        except Exception as e:
            print(f'  [错误] 处理失败: {e}')
            batch_summary[exp_name] = {'status': 'error', 'error': str(e)}
    
    # 生成批量汇总表格
    print('\n' + '=' * 120)
    print('批量处理汇总')
    print('=' * 120)
    
    # 表头 - 增加步数差异列
    header = '| {:^40} | {:^6} | {:^10} | {:^10} | {:^10} | {:^30} |'.format(
        'Experiment', 'Tasks', 'Inter Avg', 'Final Avg', 'Avg Time', 'Step Diff (L1/L2/L3/L4)')
    print('+' + '-' * 42 + '+' + '-' * 8 + '+' + '-' * 12 + '+' + '-' * 12 + '+' + '-' * 12 + '+' + '-' * 32 + '+')
    print(header)
    print('+' + '-' * 42 + '+' + '-' * 8 + '+' + '-' * 12 + '+' + '-' * 12 + '+' + '-' * 12 + '+' + '-' * 32 + '+')
    
    for exp_name, data in batch_summary.items():
        if data.get('status') == 'success' and 'summary' in data:
            overall = data['summary'].get('_overall', {})
            task_count = overall.get('total_task_count', '-')
            inter_avg = overall.get('intermediate_avg_percent')
            final_avg = overall.get('final_avg_percent')
            avg_time = overall.get('avg_per_step_all_tasks')
            
            inter_str = f'{inter_avg:.2f}%' if inter_avg is not None else '-'
            final_str = f'{final_avg:.2f}%' if final_avg is not None else '-'
            time_str = f'{avg_time:.2f}s' if avg_time is not None else '-'
            
            # 获取步数差异信息
            step_diffs = overall.get('step_diffs', {})
            step_diff_parts = []
            for level in ['l1', 'l2', 'l3', 'l4']:
                diff = step_diffs.get(level)
                if diff is not None:
                    step_diff_parts.append(f'{diff:+.1f}')
                else:
                    step_diff_parts.append('-')
            step_diff_str = '/'.join(step_diff_parts)
            
            # 截断过长的实验名
            exp_display = exp_name[:38] + '..' if len(exp_name) > 40 else exp_name
            print('| {:^40} | {:^6} | {:^10} | {:^10} | {:^10} | {:^30} |'.format(
                exp_display, task_count, inter_str, final_str, time_str, step_diff_str))
        else:
            status = data.get('status', 'unknown')
            exp_display = exp_name[:38] + '..' if len(exp_name) > 40 else exp_name
            print('| {:^40} | {:^6} | {:^10} | {:^10} | {:^10} | {:^30} |'.format(
                exp_display, '-', f'({status})', '-', '-', '-'))
    
    print('+' + '-' * 42 + '+' + '-' * 8 + '+' + '-' * 12 + '+' + '-' * 12 + '+' + '-' * 12 + '+' + '-' * 32 + '+')
    
    # 保存批量汇总到文件
    batch_summary_path = os.path.join(root, 'batch_summary.json')
    with open(batch_summary_path, 'w', encoding='utf-8') as f:
        json.dump(batch_summary, f, ensure_ascii=False, indent=2)
    print(f'\n批量汇总已保存到: {batch_summary_path}')


def main():
    extract_results()
    aggregate()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='统计和汇总实验结果（含步数差异分析）')
    parser.add_argument('--batch', '-b', action='store_true',
                        help='批量处理 result_cache 目录下的所有实验')
    parser.add_argument('--result-cache', type=str, default='result_cache',
                        help='result_cache 目录路径 (默认: result_cache)')
    parser.add_argument('--hf-result', type=str, default='hf_result',
                        help='hf_result 目录路径 (默认: hf_result)')
    args = parser.parse_args()
    
    if args.batch:
        batch_process_result_cache(args.result_cache)
    else:
        extract_results(hf_result_root=args.hf_result)
        aggregate(hf_result_root=args.hf_result)