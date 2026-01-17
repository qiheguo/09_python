import streamlit as st
import time

# 设置网页配置
st.set_page_config(page_title="BibTeX 缩写工具", layout="centered")

st.title('BibTeX 期刊名自动缩写工具')
st.markdown("上传你的 .bib 文件，本工具将自动把期刊全名替换为标准缩写。")

# --- 1. 加载缩写数据库 ---
@st.cache_data
def load_journal_list():
    journal_map = []
    try:
        # 尝试以 utf-8 读取，如果失败则尝试 latin-1 (防止编码错误)
        try:
            with open('journal_list.txt', 'r', encoding='utf-8') as fr:
                lines = fr.readlines()
        except UnicodeDecodeError:
            with open('journal_list.txt', 'r', encoding='latin-1') as fr:
                lines = fr.readlines()
                
        for line in lines:
            if " = " in line:
                parts = line.strip().split(" = ")
                if len(parts) >= 2:
                    full = parts[0]
                    short = parts[1]
                    # 格式化为 BibTeX 格式 {Full Name}
                    full_fmt = '{%s}' % full
                    short_fmt = '{%s}' % short
                    
                    if full != full.upper() and (' ' in full):
                        journal_map.append((full_fmt, short_fmt))
        return journal_map
    except FileNotFoundError:
        return []

# --- 2. 文件上传组件 ---
uploaded_file = st.file_uploader("请选择 reference.bib 文件", type=['bib', 'txt'])

# --- 3. 处理逻辑 (含修改报告) ---
if uploaded_file is not None:
    # 读取内容
    bib_content = uploaded_file.getvalue().decode("utf-8", errors='ignore')
    st.info(f"文件已读取，正在分析并替换...")

    replacements = load_journal_list()
    
    if not replacements:
        st.error("错误：找不到 journal_list.txt 文件，请确保它在同一目录下。")
    else:
        # === 核心修改部分开始 ===
        processed_content = bib_content
        changes_log = [] # 用来存修改记录
        
        # 创建一个进度条
        progress_bar = st.progress(0)
        status_text = st.empty() # 用来显示动态文字
        
        total_items = len(replacements)
        
        # 开始循环替换
        # 为了提升速度，我们不在每次循环都更新进度条，而是每隔一部分更新一次
        update_step = int(total_items / 100) 

        for i, (full, short) in enumerate(replacements):
            # 只有当全名存在于文本中时，我们才记录并替换
            # 注意：count可能会稍微增加耗时，但在Web端通常可接受
            if full in processed_content:
                count = processed_content.count(full)
                processed_content = processed_content.replace(full, short)
                # 记录修改日志
                changes_log.append(f"✅ 替换 {count} 处: {full}  ->  {short}")
            
            # 更新进度条
            if i % update_step == 0:
                progress_bar.progress(min(i / total_items, 1.0))
        
        progress_bar.progress(1.0) # 确保进度条走完
        status_text.text("处理完成！")
        
        # === 核心修改部分结束 ===

        # --- 4. 结果展示区域 ---
        st.success(f"成功！共完成了 {len(changes_log)} 个期刊名的缩写替换。")

        # 使用 Expander (折叠面板) 来展示详细日志，避免刷屏
        with st.expander("点击查看详细替换列表"):
            if changes_log:
                for log in changes_log:
                    st.text(log)
            else:
                st.write("没有发现需要替换的期刊名 (可能文件中已经是缩写，或者不在数据库中)。")

        # --- 5. 下载按钮 ---
        original_name = uploaded_file.name
        new_name = f"abbreviated_{original_name}"
        
        st.download_button(
            label="⬇️ 下载处理后的文件",
            data=processed_content,
            file_name=new_name,
            mime="text/plain"
        )