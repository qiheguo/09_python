import streamlit as st
import re

# --- 页面配置 ---
st.set_page_config(
    page_title="BibTeX 智能处理工具 - by Guo", 
    page_icon="📚",
    layout="centered",
    menu_items={
        'Get Help': 'https://github.com/qiheguo/09_python.git', # 这里也可以放你的GitHub地址
        'Report a bug': 'https://github.com/qiheguo/09_python.git',
        'About': "# BibTeX Tool by GuoQihe. \n这是一个用于学术文献管理的辅助工具。"
    }
)

# --- 样式美化 (可选) ---
# 隐藏 Streamlit 默认的汉堡菜单和页脚，用我们要自定义的
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- 标题区 ---
st.title('📚 BibTeX 智能处理工具')
st.markdown("""
上传 .bib 文件，自动缩写期刊名，并可清洗冗余 DOI。
""")

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

# --- 2. 清洗 DOI/URL 冲突逻辑 ---
def clean_doi_conflict(content):
    content = "\n" + content
    entries = re.split(r'(\n@)', content) 
    cleaned_entries = []
    removed_count = 0
    buffer = ""
    
    for part in entries:
        if part == '\n@':
            buffer = part
        else:
            full_entry = buffer + part
            buffer = "" 
            if not full_entry.strip(): continue

            lower_entry = full_entry.lower()
            has_url = 'url =' in lower_entry or 'url=' in lower_entry
            has_doi = 'doi =' in lower_entry or 'doi=' in lower_entry
            
            if has_url and has_doi:
                full_entry, n = re.subn(r'(?m)^\s*doi\s*=.*(\r?\n)?', '', full_entry, flags=re.IGNORECASE)
                if n > 0:
                    removed_count += 1
            cleaned_entries.append(full_entry)
            
    return "".join(cleaned_entries).strip(), removed_count

# --- 3. 侧边栏：设置与作者信息 ---
with st.sidebar:
    st.header("⚙️ 功能设置")
    enable_abbr = st.checkbox("启用期刊缩写替换", value=True)
    enable_doi_clean = st.checkbox("存在URL时删除DOI", value=True, help="当 BibTeX 条目同时包含 URL 和 DOI 时，保留 URL，删除 DOI 行。")
    
    st.markdown("---")
    
    # === ✨ 作者展示区 ✨ ===
    st.header("👤 关于作者")
    st.markdown("""
    **Developer:** GuoQihe  
    这是一个开源工具，旨在帮助科研人员更高效地管理参考文献。
    """)
    
    # 这里的链接请替换成你真实的 GitHub 仓库地址
    github_url = "https://github.com/qiheguo/09_python.git" # <--- TODO: 修改这里
    st.link_button("🌟 Star on GitHub", github_url)
    
    st.markdown(f"[查看源码]({github_url})")


# --- 4. 主文件上传区 ---
uploaded_file = st.file_uploader("请选择 reference.bib 文件", type=['bib', 'txt'])

# --- 5. 处理逻辑 ---
if uploaded_file is not None:
    bib_content = uploaded_file.getvalue().decode("utf-8", errors='ignore')
    st.info(f"文件已读取，开始处理...")
    
    processed_content = bib_content
    logs = []

    # 步骤 A: 清洗 DOI
    if enable_doi_clean:
        processed_content, doi_removed_num = clean_doi_conflict(processed_content)
        if doi_removed_num > 0:
            logs.append(f"🧹 [DOI 清洗] 删除了 {doi_removed_num} 个冗余 DOI (因已有 URL)。")
        else:
            logs.append("🧹 [DOI 清洗] 未发现冲突条目。")

    # 步骤 B: 缩写替换
    if enable_abbr:
        replacements = load_journal_list()
        if not replacements:
            st.error("错误：找不到 journal_list.txt 文件。")
        else:
            abbr_count = 0
            progress_bar = st.progress(0)
            status_text = st.empty()
            total_items = len(replacements)
            update_step = int(total_items / 100) if total_items > 100 else 1

            for i, (full, short) in enumerate(replacements):
                if full in processed_content:
                    count = processed_content.count(full)
                    processed_content = processed_content.replace(full, short)
                    logs.append(f"✅ [缩写] {full} -> {short} (共 {count} 处)")
                    abbr_count += 1
                
                if i % update_step == 0:
                    progress_bar.progress(min(i / total_items, 1.0))
            
            progress_bar.progress(1.0)
            status_text.text("处理完成！")
            
            if abbr_count == 0:
                logs.append("ℹ️ [缩写] 未发现需要缩写的期刊名。")

    st.success("处理完毕！")

    with st.expander("查看详细处理日志"):
        for log in logs:
            st.text(log)

    original_name = uploaded_file.name
    new_name = f"processed_{original_name}"
    
    st.download_button(
        label="⬇️ 下载处理后的文件",
        data=processed_content,
        file_name=new_name,
        mime="text/plain"
    )

# --- 6. 页面底部版权 ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: grey;'>
        有问题请联系 <b>GuoQihe</b> | qiheguo53@gmail.com 
        <a href='https://github.com/qiheguo/09_python.git' target='_blank'>GitHub Source Code</a>
    </div>
    """, 
    unsafe_allow_html=True
)