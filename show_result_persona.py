
import os
import re
import json
import statistics
import shutil
import argparse
from collections import defaultdict

def ComparePersona(taskName: str) -> str:
    """
    根据任务名称确定其所属的角色 (Persona)。
    """
    lowerName = taskName.lower()
    if any(sub in lowerName for sub in ["acc", "pro", "mar", "fin", "sal"]):
        return "Business/Management"
    if any(sub in lowerName for sub in ["adm", "hr", "cus"]):
        return "Administrative/Support"
    if any(sub in lowerName for sub in ["sof", "it", "dat"]):
        return "Technical/IT"
    if any(sub in lowerName for sub in ["des", "con", "soc"]):
        return "Creative/Content"
    return "General User"

def ParseScoresFromText(text: str):
    """
    从文本中解析中间分数和最终分数。
    """
    # 尝试直接匹配 "Intermediate Score: x, Final Result: y"
    m = re.search(r'Intermediate Score:\s*([0-9+\-\.eE]+)\s*,\s*Final Result:\s*([0-9+\-\.eE]+)', text)
    if m:
        try:
            inter = float(m.group(1))
            final = float(m.group(2))
            return inter, final
        except (ValueError, IndexError):
            pass
    # 宽松匹配：分别找 Intermediate 和 Final 的数字
    m1 = re.search(r'Intermediate Score:\s*([0-9+\-\.eE]+)', text)
    m2 = re.search(r'Final Result:\s*([0-9+\-\.eE]+)', text)
    if m1 and m2:
        try:
            return float(m1.group(1)), float(m2.group(1))
        except (ValueError, IndexError):
            return None
    # 兜底方案：寻找文本中的任意两个数字
    nums = re.findall(r'([0-9]+(?:\.[0-9]+)?)', text)
    if len(nums) >= 2:
        try:
            return float(nums[0]), float(nums[1])
        except (ValueError, IndexError):
            pass
    return None

def CalculatePersonaScores(hfResultRoot='hf_result', save_summary=True):
    """
    计算并返回每个 Persona 的平均分数，同时可选将结果保存为 summary_report.json。
    返回一个字典用于外部汇总。
    """
    root = os.path.abspath(hfResultRoot)
    if not os.path.isdir(root):
        print(f"错误：目录不存在 -> {root}")
        return None

    personaScores = defaultdict(lambda: {"intermediate": [], "final": []})

    for taskName in sorted(os.listdir(root)):
        # 跳过 L4 级别任务统计中间分数
        if "l4" in taskName.lower():
            continue

        taskPath = os.path.join(root, taskName)
        if not os.path.isdir(taskPath):
            continue

        # 查找最新的时间戳子文件夹
        subdirs = [d for d in os.listdir(taskPath) if os.path.isdir(os.path.join(taskPath, d))]
        if not subdirs:
            continue

        latestSubdir = sorted(subdirs, reverse=True)[0]
        resultJsonPath = os.path.join(taskPath, latestSubdir, 'result.json')

        if os.path.isfile(resultJsonPath):
            try:
                with open(resultJsonPath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    parsedScores = ParseScoresFromText(content)

                if parsedScores:
                    interScore, finalScore = parsedScores
                    persona = ComparePersona(taskName)
                    personaScores[persona]["intermediate"].append(interScore)
                    personaScores[persona]["final"].append(finalScore)
            except Exception as e:
                print(f"处理文件时出错 {resultJsonPath}: {e}")

    # 组织输出结构化数据
    report = {"personas": {}, "_meta": {"source_root": root}}
    for persona, scores in sorted(personaScores.items()):
        inter_list = scores.get("intermediate", [])
        final_list = scores.get("final", [])
        taskCount = len(inter_list)
        avgIntermediate = statistics.mean(inter_list) * 100 if inter_list else None
        avgFinal = statistics.mean(final_list) * 100 if final_list else None

        report["personas"][persona] = {
            "task_count": taskCount,
            "intermediate_avg_percent": round(avgIntermediate, 2) if avgIntermediate is not None else None,
            "final_avg_percent": round(avgFinal, 2) if avgFinal is not None else None,
        }

    if save_summary:
        out_path = os.path.join(root, 'summary_report.json')
        try:
            with open(out_path, 'w', encoding='utf-8') as fo:
                json.dump(report, fo, ensure_ascii=False, indent=2)
            print(f'已将 Persona 汇总保存到: {out_path}')
        except Exception as e:
            print(f'保存 summary_report.json 失败: {e}')

    # 也打印一份简要摘要到控制台
    print("=" * 50)
    print("各 Persona 平均分数统计")
    print("=" * 50)
    for persona, info in sorted(report["personas"].items()):
        print(f"Persona: {persona} (任务数: {info['task_count']})")
        ia = info.get('intermediate_avg_percent')
        fa = info.get('final_avg_percent')
        print(f"  - 平均中间分数: {ia:.2f}%" if ia is not None else "  - 平均中间分数: -")
        print(f"  - 平均最终分数: {fa:.2f}%" if fa is not None else "  - 平均最终分数: -")
    print("\n" + "=" * 50)

    return report

def batch_process_result_cache(result_cache_root='result_cache'):
    """
    批量处理 result_cache 目录下的所有实验结果（按 Persona 分类）。
    
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
    - 生成总览文件 result_cache/batch_summary_persona.json
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
    print(f'批量处理 result_cache 下的 {len(experiment_dirs)} 个实验 (按 Persona 分类)')
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
        
        # 使用 CalculatePersonaScores 函数处理该实验目录
        try:
            report = CalculatePersonaScores(hfResultRoot=result_root, save_summary=True)
            
            if report:
                batch_summary[exp_name] = {
                    'status': 'success',
                    'summary': report
                }
            else:
                batch_summary[exp_name] = {'status': 'no_data', 'task_count': len(task_dirs)}
                
        except Exception as e:
            print(f'  [错误] 处理失败: {e}')
            batch_summary[exp_name] = {'status': 'error', 'error': str(e)}
    
    # 生成批量汇总表格
    print('\n' + '=' * 120)
    print('批量处理汇总（按 Persona）')
    print('=' * 120)
    
    # 表头
    header = '| {:^40} | {:^6} | {:^15} | {:^15} | {:^15} | {:^15} |'.format(
        'Experiment', 'Tasks', 'Bus/Mgmt', 'Admin/Support', 'Tech/IT', 'Creative')
    print('+' + '-' * 42 + '+' + '-' * 8 + '+' + '-' * 17 + '+' + '-' * 17 + '+' + '-' * 17 + '+' + '-' * 17 + '+')
    print(header)
    print('+' + '-' * 42 + '+' + '-' * 8 + '+' + '-' * 17 + '+' + '-' * 17 + '+' + '-' * 17 + '+' + '-' * 17 + '+')
    
    for exp_name, data in batch_summary.items():
        if data.get('status') == 'success' and 'summary' in data:
            personas = data['summary'].get('personas', {})
            
            # 计算总任务数
            task_count = sum(p.get('task_count', 0) for p in personas.values())
            
            # 提取各 Persona 的最终分数均值
            bus_mgmt = personas.get('Business/Management', {}).get('final_avg_percent')
            admin = personas.get('Administrative/Support', {}).get('final_avg_percent')
            tech = personas.get('Technical/IT', {}).get('final_avg_percent')
            creative = personas.get('Creative/Content', {}).get('final_avg_percent')
            
            bus_str = f'{bus_mgmt:.1f}%' if bus_mgmt is not None else '-'
            admin_str = f'{admin:.1f}%' if admin is not None else '-'
            tech_str = f'{tech:.1f}%' if tech is not None else '-'
            creative_str = f'{creative:.1f}%' if creative is not None else '-'
            
            # 截断过长的实验名
            exp_display = exp_name[:38] + '..' if len(exp_name) > 40 else exp_name
            print('| {:^40} | {:^6} | {:^15} | {:^15} | {:^15} | {:^15} |'.format(
                exp_display, task_count, bus_str, admin_str, tech_str, creative_str))
        else:
            status = data.get('status', 'unknown')
            exp_display = exp_name[:38] + '..' if len(exp_name) > 40 else exp_name
            print('| {:^40} | {:^6} | {:^15} | {:^15} | {:^15} | {:^15} |'.format(
                exp_display, '-', f'({status})', '-', '-', '-'))
    
    print('+' + '-' * 42 + '+' + '-' * 8 + '+' + '-' * 17 + '+' + '-' * 17 + '+' + '-' * 17 + '+' + '-' * 17 + '+')
    
    # 保存批量汇总到文件
    batch_summary_path = os.path.join(root, 'batch_summary_persona.json')
    with open(batch_summary_path, 'w', encoding='utf-8') as f:
        json.dump(batch_summary, f, ensure_ascii=False, indent=2)
    print(f'\n批量汇总已保存到: {batch_summary_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='按 Persona 统计实验结果')
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
        CalculatePersonaScores(hfResultRoot=args.hf_result)

