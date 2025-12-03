import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
from io import StringIO, BytesIO
import time

# -------------------------------------------------------------
# Translator + cache
# -------------------------------------------------------------
@st.cache_resource
def get_translator(source_lang, target_lang):
    return GoogleTranslator(source=source_lang, target=target_lang)

cache = {}

def translate_text_string(text, translator):
    """Translate a single string with caching + retry."""
    if text is None or str(text).strip() == "":
        return text
    
    s = str(text).strip()
    if s in cache:
        return cache[s]

    for _ in range(3):
        try:
            zh = translator.translate(s)
            cache[s] = zh
            time.sleep(0.05)
            return zh
        except Exception:
            time.sleep(1)

    return s  # fallback on failure


# -------------------------------------------------------------
# File translators (in-memory)
# -------------------------------------------------------------
def translate_csv_file(uploaded_file, translator):
    df = pd.read_csv(uploaded_file)

    # Translate headers
    new_cols = [translate_text_string(col, translator) for col in df.columns]
    df.columns = new_cols

    # Translate all cell values
    df = df.apply(lambda col: col.map(lambda v: translate_text_string(v, translator)))

    # Convert to CSV string
    buffer = StringIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig")
    buffer.seek(0)
    return buffer.getvalue()


def translate_txt_file(uploaded_file, translator):
    content = uploaded_file.read().decode("utf-8", errors="ignore")
    translated = translate_text_string(content, translator)
    return translated

def translate_excel_file(uploaded_file, translator):
    """
    Translate all sheets in an Excel file using openpyxl backend (no xlsxwriter needed).
    - Translates column headers
    - Translates all cell values
    """
    sheets = pd.read_excel(uploaded_file, sheet_name=None, engine="openpyxl")

    translated_sheets = {}
    for sheet_name, df in sheets.items():
        # Translate headers
        new_cols = [translate_text_string(col, translator) for col in df.columns]
        df.columns = new_cols

        # Translate all cell values
        df = df.apply(lambda col: col.map(lambda v: translate_text_string(v, translator)))
        translated_sheets[sheet_name] = df

    # Write to an Excel file using openpyxl
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, df in translated_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    buffer.seek(0)
    return buffer.getvalue()


# -------------------------------------------------------------
# Streamlit UI
# -------------------------------------------------------------

def main():
    st.set_page_config(page_title="CSV/TXT/Excel Translator", page_icon="🌐", layout="centered")

    st.title("🌐 CSV / TXT / Excel Translator")
    st.write("Upload a `.csv`, `.txt` or Excel (`.xlsx`/`.xls`) file and translate it using Google Translator via `deep-translator`.")

    # Language selection
    col1, col2 = st.columns(2)
    with col1:
        source_lang = st.text_input("Source language (code or 'auto')", value="en")
    with col2:
        target_lang = st.text_input("Target language (e.g. 'zh-CN')", value="zh-CN")

    uploaded_file = st.file_uploader(
        "Upload CSV, TXT, or Excel file",
        type=["csv", "txt", "xlsx", "xls"]
    )

    if uploaded_file is not None:
        st.info(f"Detected file: `{uploaded_file.name}`")

        if st.button("🚀 Translate"):
            with st.spinner("Translating... This may take a while for large files."):
                translator = get_translator(source_lang, target_lang)

                filename = uploaded_file.name
                lower_name = filename.lower()

                if lower_name.endswith(".csv"):
                    try:
                        translated_content = translate_csv_file(uploaded_file, translator)
                        out_name = filename.rsplit(".", 1)[0] + "_translated.csv"
                        st.success("✅ CSV translation complete!")

                        st.download_button(
                            label="⬇️ Download translated CSV",
                            data=translated_content,
                            file_name=out_name,
                            mime="text/csv",
                        )
                    except Exception as e:
                        st.error(f"Error translating CSV: {e}")

                elif lower_name.endswith(".txt"):
                    try:
                        translated_content = translate_txt_file(uploaded_file, translator)
                        out_name = filename.rsplit(".", 1)[0] + "_translated.txt"
                        st.success("✅ TXT translation complete!")

                        st.download_button(
                            label="⬇️ Download translated TXT",
                            data=translated_content.encode("utf-8"),
                            file_name=out_name,
                            mime="text/plain",
                        )
                    except Exception as e:
                        st.error(f"Error translating TXT: {e}")

                elif lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
                    try:
                        translated_content = translate_excel_file(uploaded_file, translator)
                        out_name = filename.rsplit(".", 1)[0] + "_translated.xlsx"
                        st.success("✅ Excel translation complete!")

                        st.download_button(
                            label="⬇️ Download translated Excel",
                            data=translated_content,
                            file_name=out_name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    except Exception as e:
                        st.error(f"Error translating Excel: {e}")

                else:
                    st.error("❌ Unsupported file type. Only .csv, .txt, .xlsx, and .xls are supported.")


if __name__ == "__main__":
    main()
