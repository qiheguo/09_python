import streamlit as st
import re # 导入正则库

# 设置网页配置
st.set_page_config(page_title="BibTeX 缩写与清洗工具", layout="centered")

st.title('BibTeX 智能处理工具')
st.markdown("上传 .bib 文件，自动缩写期刊名，并可选择清理冗余的 DOI。")

# --- 1. 加载缩写数据库 ---
@st.cache_data
def load_journal_list():
    journal_map = []
    try:
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
                    full_fmt = '{%s}' % full
                    short_fmt = '{%s}' % short
                    
                    if full != full.upper() and (' ' in full):
                        journal_map.append((full_fmt, short_fmt))
        return journal_map
    except FileNotFoundError:
        return []

# --- 新增功能: 清洗 DOI/URL 冲突 ---
def clean_doi_conflict(content):
    """
    逻辑：
    1. 按 '@' 分割条目
    2. 对每个条目检查，如果同时含有 'url =' 和 'doi =' (忽略大小写)
    3. 删除 doi 那一行
    """
    # 为了避免 split 吃掉分隔符，我们先在所有 @ 前加个特殊标记，或者手动拆分
    # 简单的做法是按 \n@ 拆分 (假设BibTeX格式标准)
    # 为了处理方便，我们先给开头补一个换行
    content = "\n" + content
    entries = re.split(r'(\n@)', content) 
    
    cleaned_entries = []
    removed_count = 0
    
    # split后列表会是 ['', '\n@', 'article{...', '\n@', 'book{...']
    # 我们需要重组
    buffer = ""
    
    for part in entries:
        if part == '\n@':
            buffer = part
        else:
            full_entry = buffer + part
            buffer = "" # 重置
            
            if not full_entry.strip(): 
                continue

            # --- 核心判断逻辑 ---
            # 检查这个条目里是否有 url 和 doi 字段
            # 使用简单的字符串包含检查 (转小写)
            lower_entry = full_entry.lower()
            has_url = 'url =' in lower_entry or 'url=' in lower_entry
            has_doi = 'doi =' in lower_entry or 'doi=' in lower_entry
            
            if has_url and has_doi:
                # 使用正则删除 doi 行
                # 正则解释: 
                # (?m) 多行模式
                # ^\s*doi\s*= 匹配行首(允许空格)的doi=
                # .* 匹配这行剩下的所有内容
                # \n? 匹配可能存在的换行符
                full_entry, n = re.subn(r'(?m)^\s*doi\s*=.*(\r?\n)?', '', full_entry, flags=re.IGNORECASE)
                if n > 0:
                    removed_count += 1
            
            cleaned_entries.append(full_entry)
            
    return "".join(cleaned_entries).strip(), removed_count

# --- 2. 侧边栏配置区 ---
st.sidebar.header("功能设置")
enable_abbr = st.sidebar.checkbox("启用期刊缩写替换", value=True)
enable_doi_clean = st.sidebar.checkbox("若同时存在URL和DOI，删除DOI", value=True, help="当一个文献条目同时包含 URL 和 DOI 字段时，保留 URL，删除 DOI 行。")

# --- 3. 文件上传组件 ---
uploaded_file = st.file_uploader("请选择 reference.bib 文件", type=['bib', 'txt'])

# --- 4. 处理逻辑 ---
if uploaded_file is not None:
    # 读取内容
    bib_content = uploaded_file.getvalue().decode("utf-8", errors='ignore')
    st.info(f"文件已读取，正在处理...")
    
    processed_content = bib_content
    logs = []

    # === 步骤 A: 清洗 DOI (如果你勾选了的话) ===
    if enable_doi_clean:
        processed_content, doi_removed_num = clean_doi_conflict(processed_content)
        if doi_removed_num > 0:
            logs.append(f"🧹 清理冲突: 删除了 {doi_removed_num} 个冗余的 DOI 字段 (因为该条目已有 URL)。")
        else:
            logs.append("🧹 清理冲突: 未发现同时存在 DOI 和 URL 的条目，无需删除。")

    # === 步骤 B: 缩写替换 (如果你勾选了的话) ===
    if enable_abbr:
        replacements = load_journal_list()
        if not replacements:
            st.error("错误：找不到 journal_list.txt 文件。")
        else:
            abbr_count = 0
            # 进度条逻辑
            progress_bar = st.progress(0)
            status_text = st.empty()
            total_items = len(replacements)
            update_step = int(total_items / 100) 

            for i, (full, short) in enumerate(replacements):
                if full in processed_content:
                    count = processed_content.count(full)
                    processed_content = processed_content.replace(full, short)
                    logs.append(f"✅ 缩写替换: {full} -> {short} (共 {count} 处)")
                    abbr_count += 1
                
                if i % update_step == 0:
                    progress_bar.progress(min(i / total_items, 1.0))
            
            progress_bar.progress(1.0)
            status_text.text("处理完成！")
            
            if abbr_count == 0:
                logs.append("ℹ️ 缩写检查: 未发现需要缩写的期刊名。")

    # --- 5. 结果展示区域 ---
    st.success("所有操作执行完毕！")

    with st.expander("查看详细处理日志"):
        for log in logs:
            st.text(log)

    # --- 6. 下载按钮 ---
    original_name = uploaded_file.name
    new_name = f"processed_{original_name}"
    
    st.download_button(
        label="⬇️ 下载处理后的文件",
        data=processed_content,
        file_name=new_name,
        mime="text/plain"
    )