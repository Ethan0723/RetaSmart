import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output

# 定义数据源文件夹的路径
data_folder = "data"

# 创建一个空的DataFrame用于存储所有的数据
all_data = pd.DataFrame()

# 遍历数据源文件夹中的每一个Excel文件
for file_name in os.listdir(data_folder):
    if file_name.endswith('.xlsx'):
        file_path = os.path.join(data_folder, file_name)
        
        try:
            # 读取Excel文件，尝试使用不同的引擎
            data = pd.read_excel(file_path, engine='openpyxl')
        except Exception as e:
            print(f"Error reading file {file_path} with openpyxl: {e}")
            try:
                data = pd.read_excel(file_path, engine='xlrd')
            except Exception as e:
                print(f"Error reading file {file_path} with xlrd: {e}")
                continue

        # 在数据中添加新的列，列名为'Channel_code'，值为当前文件名（不包含扩展名）
        data['industry'] = os.path.splitext(file_name)[0]
        
        # 将读取的数据追加到总的DataFrame中
        all_data = pd.concat([all_data, data], ignore_index=True)
df1 = all_data.dropna(subset=['store qty type'])
# 按行业、店铺数量类型、州和城市进行分组，并聚合计算商家数量和店铺数量
df1 = df1.groupby(['industry', 'store qty type', 'yellow pages state', 'yellow pages city']).agg(
    merchant_qty=('Name', pd.Series.nunique),
    store_qty=('Address', 'count')
).reset_index()

# 将 'store qty type' 字段转换为文本格式
df1['store qty type'] = df1['store qty type'].astype(str)

city_info = pd.read_excel(r'city_ifno/city.xlsx', engine='openpyxl')

df = pd.merge(df1, city_info, how='left', on=['yellow pages city', 'yellow pages state'])
# 获取唯一的行业和店铺数量类型列表
industries = df['industry'].unique()
store_qty_types = df['store qty type'].unique()

# 对店铺数量类型进行排序，并添加 "All" 选项
store_qty_types_sorted = sorted(store_qty_types, key=lambda x: (int(x.split('~')[0]) if '~' in x else (int(x[:-1]) if x.endswith('+') else int(x))))
store_qty_types_sorted.insert(0, 'All')

# 创建 Dash 应用程序
app = Dash(__name__)

app.layout = html.Div([
    html.H1("美国各州店铺数量热力图"),
    html.Div([
        html.Label("选择行业:", style={'margin-right': '10px'}),
        dcc.Dropdown(
            id='industry-dropdown',
            options=[{'label': industry, 'value': industry} for industry in industries],
            value=industries[0],
            style={'width': '200px'}
        ),
        html.Label("选择店铺数量类型:", style={'margin-left': '20px', 'margin-right': '10px'}),
        dcc.Dropdown(
            id='store-qty-type-dropdown',
            options=[{'label': qty_type, 'value': qty_type} for qty_type in store_qty_types_sorted],
            value='All',
            style={'width': '200px'}
        )
    ], style={'display': 'flex', 'align-items': 'center'}),
    dcc.Graph(id='heatmap', style={'height': '80vh'})  # 调整图表高度
])

@app.callback(
    Output('heatmap', 'figure'),
    [Input('industry-dropdown', 'value'),
     Input('store-qty-type-dropdown', 'value')]
)
def update_heatmap(selected_industry, selected_store_qty_type):
    # 筛选数据
    if selected_store_qty_type == 'All':
        filtered_df = df[df['industry'] == selected_industry]
    else:
        filtered_df = df[(df['industry'] == selected_industry) & 
                         (df['store qty type'] == selected_store_qty_type)]

    # 聚合数据，计算每个州的商家数量和店铺数量
    grouped_df = filtered_df.groupby(['yellow pages state']).agg({
        'store_qty': 'sum'
    }).reset_index()

    # 生成颜色条，颜色根据店铺数量来区分
    colorscale = [[0, 'blue'], [0.5, 'yellow'], [1, 'red']]

    # 绘制统一颜色的地图
    fig = go.Figure()

    fig.add_trace(go.Choropleth(
        locations=grouped_df['yellow pages state'],
        z=[1] * len(grouped_df),  # 所有州的颜色值相同
        locationmode='USA-states',
        colorscale=[[0, 'rgb(44, 62, 80)'], [1, 'rgb(44, 62, 80)']],  # 统一深蓝色
        showscale=False,
        hoverinfo='none',  # 禁用悬停提示
        showlegend=False  # 禁用图例
    ))

    # 添加气泡标记和标签
    fig.add_trace(go.Scattergeo(
        locationmode='USA-states',
        locations=grouped_df['yellow pages state'],
        text=grouped_df.apply(lambda row: f"{row['yellow pages state']}<br>{row['store_qty']}", axis=1),
        mode='markers+text',
        marker=dict(
            size=10,
            color=grouped_df['store_qty'],
            colorscale=colorscale,
            colorbar=dict(title="店铺数量")
        ),
        textfont=dict(
            size=12,
            color='white'
        ),
        textposition="bottom center",
        hovertemplate='<b>%{text}</b><extra></extra>',  # 自定义提示模板
        showlegend=False  # 禁用图例
        # hoverinfo='none'  # 禁用悬停提示
    ))

    # 更新布局
    fig.update_layout(
        title_text='美国各州店铺数量热力图',
        geo=dict(
            scope='usa',
            projection=go.layout.geo.Projection(type='albers usa'),
            showlakes=True,
            lakecolor='rgb(255, 255, 255)'
        )
    )

    return fig

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=10001, debug=False)
