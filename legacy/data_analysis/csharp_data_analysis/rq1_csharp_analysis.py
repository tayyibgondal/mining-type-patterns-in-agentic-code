"""
RQ1 Analysis for C#: 'dynamic' Type Usage Analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import re
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300

def load_data():
    agent_df = pd.read_csv('../csharp_data/agent_type_prs_filtered_by_open_ai.csv')
    agent_df = agent_df[agent_df['final_is_type_related'] == True]
    
    human_df = pd.read_csv('../csharp_data/human_type_prs_filtered_by_open_ai.csv')
    human_df = human_df[human_df['final_is_type_related'] == True]
    
    print(f"Loaded - AI: {len(agent_df)}, Human: {len(human_df)}")
    return agent_df, human_df

def extract_dynamic(df):
    metrics = []
    pattern = r'\bdynamic\s+\w+|\bdynamic\>|:\s*dynamic\b|<dynamic>'
    
    for _, row in df.iterrows():
        patch = str(row.get('patch_text', ''))
        adds, rems = 0, 0
        
        for line in patch.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                adds += len(re.findall(pattern, line, re.IGNORECASE))
            elif line.startswith('-') and not line.startswith('---'):
                rems += len(re.findall(pattern, line, re.IGNORECASE))
        
        metrics.append({
            'id': row['id'],
            'agent': row.get('agent', 'Human'),
            'dynamic_additions': adds,
            'dynamic_removals': rems,
            'net_change': adds - rems,
            'total_ops': adds + rems
        })
    
    return pd.DataFrame(metrics)

if __name__ == "__main__":
    print("=" * 60)
    print("C# RQ1: dynamic Type Analysis")
    print("=" * 60)
    
    agent_df, human_df = load_data()
    agent_m = extract_dynamic(agent_df)
    human_m = extract_dynamic(human_df)
    
    print(f"\nWith dynamic changes: AI={( agent_m['total_ops'] > 0).sum()}, Human={(human_m['total_ops'] > 0).sum()}")
    
    agent_m.to_csv('figures_rq1/agent_dynamic_metrics.csv', index=False)
    human_m.to_csv('figures_rq1/human_dynamic_metrics.csv', index=False)
    
    print("Complete!")
