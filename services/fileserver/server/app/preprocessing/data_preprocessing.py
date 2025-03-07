import pandas as pd
import numpy as np

def preprocess_game_data(csv_path):
    """
    预处理游戏数据CSV文件
    
    Args:
        csv_path: CSV文件路径
    
    Returns:
        处理后的DataFrame
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(csv_path)
        
        # 1. 处理Year_of_Release列
        # 转换为数值类型，非数值将变为NaN
        df['Year_of_Release'] = pd.to_numeric(df['Year_of_Release'], errors='coerce')
        
        # 过滤条件：
        # 1. Year_of_Release不为空
        # 2. Year_of_Release小于等于2016
        df = df[
            df['Year_of_Release'].notna() & 
            (df['Year_of_Release'] <= 2016)
        ]
        
        # 将Year_of_Release转换为整数类型
        df['Year_of_Release'] = df['Year_of_Release'].astype(int)
        
        # 保存处理后的数据
        output_path = csv_path.replace('.csv', '_processed.csv')
        df.to_csv(output_path, index=False)
        print(f"处理后的数据已保存到: {output_path}")
        
        return df
        
    except Exception as e:
        print(f"数据预处理时发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    # 测试代码
    try:
        csv_path = "../../csvs/vgsales1.csv"  # 替换为实际的CSV文件路径
        df = preprocess_game_data(csv_path)
        print("数据预处理完成")
        print(f"处理后的数据行数: {len(df)}")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")