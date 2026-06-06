"""
P0 Sensitivity Analysis - Run all 3 experiments
Recreated from original script.

Usage:
  python run_p0_sensitivity.py
"""
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT = Path(r'C:\Users\enmusubi4\Desktop\pinn-reliability-paper')
CONFIGS_DIR = PROJECT / 'minimal_pinn' / 'configs'
RESULTS_DIR = PROJECT / 'experiments' / 'results'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def run_experiment(config, run_name, timeout=3600):
    config['run_name'] = run_name
    config_path = CONFIGS_DIR / f'{run_name}.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    output_dir = RESULTS_DIR / run_name
    cmd = [sys.executable, '-m', 'minimal_pinn.run_experiment',
           '--config', str(config_path), '--output-dir', str(output_dir)]
    
    start = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(PROJECT))
        elapsed = time.time() - start
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.strip().startswith('{') and 'scalar_metrics' in line:
                    metrics = eval(line.strip())
                    return {'success': True, 'rel_l2': metrics['scalar_metrics']['rel_l2'], 'elapsed': elapsed}
            return {'success': True, 'rel_l2': None, 'elapsed': elapsed}
        else:
            return {'success': False, 'error': result.stderr[-300:], 'elapsed': elapsed}
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed': time.time() - start}

def load_base_config():
    with open(CONFIGS_DIR / 'burgers_sparse_noisy.json') as f:
        config = json.load(f)
    config['data']['num_observation'] = 32
    config['data']['noise_std'] = 0.10
    config['training']['epochs'] = 500
    return config

def experiment_1_collocation():
    print('\n=== EXPERIMENT 1: Collocation Points ===')
    base = load_base_config()
    results = []
    for n_col in [2048, 4096, 8192]:
        print(f'  N_col={n_col}...', end=' ', flush=True)
        config = base.copy()
        config['data'] = dict(base['data'])
        config['data']['num_collocation'] = n_col
        config['training'] = dict(base['training'])
        r = run_experiment(config, f'sens_ncol_{n_col}')
        results.append({'n_col': n_col, **r})
        print(f'OK rel_l2={r["rel_l2"]:.4f}' if r['success'] else f'FAIL')
    return results

def experiment_2_epochs():
    print('\n=== EXPERIMENT 2: Training Epochs ===')
    base = load_base_config()
    results = []
    for epochs in [300, 500, 1000, 2000]:
        print(f'  epochs={epochs}...', end=' ', flush=True)
        config = base.copy()
        config['data'] = dict(base['data'])
        config['training'] = dict(base['training'])
        config['training']['epochs'] = epochs
        r = run_experiment(config, f'sens_epochs_{epochs}', timeout=7200)
        results.append({'epochs': epochs, **r})
        print(f'OK rel_l2={r["rel_l2"]:.4f}' if r['success'] else f'FAIL')
    return results

def experiment_3_nonlinearity():
    print('\n=== EXPERIMENT 3: Nonlinearity Ablation ===')
    base = load_base_config()
    results = []
    for nu in [0.001, 0.01, 0.1, 1.0]:
        print(f'  nu={nu}...', end=' ', flush=True)
        config = base.copy()
        config['data'] = dict(base['data'])
        config['training'] = dict(base['training'])
        config['case'] = {'name': 'burgers', 'nu': nu}
        r = run_experiment(config, f'sens_nu_{nu}')
        results.append({'nu': nu, **r})
        print(f'OK rel_l2={r["rel_l2"]:.4f}' if r['success'] else f'FAIL')
    return results

def main():
    print('P0 SENSITIVITY ANALYSIS')
    print(f'Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    r1 = experiment_1_collocation()
    r2 = experiment_2_epochs()
    r3 = experiment_3_nonlinearity()
    
    summary = {
        'timestamp': datetime.now().isoformat(),
        'collocation_sensitivity': r1,
        'epochs_sensitivity': r2,
        'nonlinearity_ablation': r3
    }
    with open(RESULTS_DIR / 'p0_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print('\n=== SUMMARY ===')
    print('Collocation:', [(r['n_col'], r['rel_l2']) for r in r1])
    print('Epochs:', [(r['epochs'], r['rel_l2']) for r in r2])
    print('Nonlinearity:', [(r['nu'], r['rel_l2']) for r in r3])

if __name__ == '__main__':
    main()
