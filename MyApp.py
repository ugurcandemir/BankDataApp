# We are creating a Streamlit application for ING Bank's Bank Analysis Platform.
# Import necessary libraries.
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import plotly.express as px
from fpdf import FPDF
from io import BytesIO
import base64
import unicodedata
import os
from markdown2 import markdown
from bs4 import BeautifulSoup
import tempfile
import pydeck as pdk
import joblib
from sklearn.preprocessing import LabelEncoder

# Set the page title, layout and other configurations.

# Set page config
st.set_page_config(page_title="ING Banka Analiz Platformu", layout="wide")

# Custom CSS for styling
st.markdown("""
    <style>
        .main {
            background-color: #ffffff;
        }
        .sidebar .sidebar-content {
            background-color: #f8f9fa;
        }
        .css-1d391kg {
            padding-top: 2rem;
        }
        .header-container {
            display: flex;
            align-items: center;
            background-color: #d50000;
            padding: 20px;
            color: white;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .header-container img {
            height: 60px;
            margin-right: 20px;
        }
        .header-text {
            font-size: 28px;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# Load local logo
logo = Image.open("ing_logo.png")

# Header section with local image
col1, col2 = st.columns([1, 1.5])
with col1:
    st.image(logo, width=8000)
with col2:
    st.markdown(
        "<h1 style='color: #FF6200; margin-top: 20px;'>Banka Analiz Platformu</h1>",
        unsafe_allow_html=True
    )




def filtered_chart_section(df, key_prefix="chart"):
    st.markdown("### 📋 Tablo")
    df = df.copy()

    # Filter by year
    years = df["Yıllar"].unique()
    selected_years = st.multiselect("Yıllara Göre Filtrele", years, default=years, key=f"{key_prefix}_years")
    df = df[df["Yıllar"].isin(selected_years)]

    # Filter by columns (excluding Yıllar)
    all_columns = df.columns.drop("Yıllar")
    selected_columns = st.multiselect("Değişkenleri Seçin", all_columns, default=all_columns[:3], key=f"{key_prefix}_cols")
    filtered_df = df[["Yıllar"] + selected_columns]
    st.dataframe(filtered_df)

    # Chart builder with export
    chart_creator_with_export(filtered_df, key_prefix=key_prefix)


def chart_creator_with_export(df, key_prefix="chart"):
    st.markdown("---")
    st.markdown("### 📊 Görsel Oluştur")

    if f"{key_prefix}_charts" not in st.session_state:
        st.session_state[f"{key_prefix}_charts"] = []

    with st.form(key=f"{key_prefix}_form"):
        chart_type = st.selectbox("Grafik Türü Seçin", ["Çizgi (Line)", "Bar", "Alan (Area)", "Pasta (Pie)", "Dağılım (Scatter)"], key=f"{key_prefix}_chart_type")
        x_col = st.selectbox("X Eksen Kolonu", df.columns, index=0, key=f"{key_prefix}_x")
        y_col = st.selectbox("Y Eksen Kolonu", df.columns, index=1 if len(df.columns) > 1 else 0, key=f"{key_prefix}_y")
        add_chart = st.form_submit_button("Grafiği Ekle")

        if add_chart:
            st.session_state[f"{key_prefix}_charts"].append((chart_type, x_col, y_col))

    # Display and export charts
    for idx, (chart_type, x_col, y_col) in enumerate(st.session_state[f"{key_prefix}_charts"]):
        st.markdown(f"#### Grafik {idx+1}: {chart_type} ({x_col} vs {y_col})")
        try:
            if chart_type == "Çizgi (Line)":
                fig = px.line(df, x=x_col, y=y_col)
            elif chart_type == "Bar":
                fig = px.bar(df, x=x_col, y=y_col)
            elif chart_type == "Alan (Area)":
                fig = px.area(df, x=x_col, y=y_col)
            elif chart_type == "Pasta (Pie)":
                fig = px.pie(df, names=x_col, values=y_col)
            elif chart_type == "Dağılım (Scatter)":
                fig = px.scatter(df, x=x_col, y=y_col)
            st.plotly_chart(fig, use_container_width=True)

            if st.session_state.get("reports"):
                export_to = st.selectbox(f"Grafik {idx+1} için rapor seçin", list(st.session_state["reports"].keys()), key=f"{key_prefix}_export_{idx}")
                if st.button(f"Grafiği '{export_to}' raporuna aktar", key=f"{key_prefix}_export_btn_{idx}"):
                    st.session_state["reports"][export_to]["charts"].append(fig)
                    st.success(f"Görsel '{export_to}' raporuna eklendi.")
        except Exception as e:
            st.warning(f"Grafik çizilirken hata oluştu: {e}")

            
def run_common_size_analysis():
    st.subheader("📈 Yüzde Analizi")
    st.write("Yüzde (common-size) analizlerinin gösterileceği alan.")
    st.markdown("## 📊 Yüzde Yöntemi ile Analiz (Common-Size Analysis)")

    # Load both datasets
    df_bilanco = pd.read_excel("ing_balance.xlsx", index_col=0)
    df_gelir = pd.read_excel("ing_income.xlsx", index_col=0)
    if "Unnamed: 1" in df_gelir.columns:
        df_gelir = df_gelir.drop(columns=["Unnamed: 1"])

    # ----------- BİLANÇO ANALİZİ -----------
    st.markdown("### 📘 Bilanço")
    bilanco_columns = df_bilanco.columns.tolist()

    selected_cols_bilanco = st.multiselect(
        "Görüntülenecek Yıllar (Bilanço)",
        bilanco_columns,
        default=bilanco_columns,
        key="bilanco_years"
    )

    if selected_cols_bilanco:
        base_column_bilanco = st.selectbox(
            "Baz Alınacak Yıl (Bilanço)",
            selected_cols_bilanco,
            key="bilanco_base"
        )

        df_bilanco_view = df_bilanco[selected_cols_bilanco]
        df_bilanco_common = df_bilanco_view.divide(df_bilanco_view[base_column_bilanco], axis=0) * 100
        st.dataframe(df_bilanco_common.style.format("{:.2f} %"))

    st.markdown("---")

    # ----------- GELİR TABLOSU ANALİZİ -----------
    st.markdown("### 📙 Gelir Tablosu")
    gelir_columns = df_gelir.columns.tolist()

    selected_cols_gelir = st.multiselect(
        "Görüntülenecek Yıllar (Gelir Tablosu)",
        gelir_columns,
        default=gelir_columns,
        key="gelir_years"
    )

    if selected_cols_gelir:
        base_column_gelir = st.selectbox(
            "Baz Alınacak Yıl (Gelir Tablosu)",
            selected_cols_gelir,
            key="gelir_base"
        )

        df_gelir_view = df_gelir[selected_cols_gelir]
        df_gelir_common = df_gelir_view.divide(df_gelir_view[base_column_gelir], axis=0) * 100
        st.dataframe(df_gelir_common.style.format("{:.2f} %"))


def run_trend_analysis():
    st.subheader("📈 Trend Analizi")
    st.write("Trend analizlerinin gösterileceği alan.")
    st.markdown("## 📈 Trend Analizi (Yatay Yüzde Değişim)")

    # ---- BİLANÇO TREND ANALİZİ ----
    # Load balance sheet data (assumes first column is "Yıllar")
    df_bilanco = pd.read_excel("ing_balance.xlsx")
    # Pivot: set "Yıllar" as index and then transpose so that rows = financial items, columns = years.
    df_bilanco_pivot = df_bilanco.set_index("Yıllar").T

    # Get the list of available years (now from the columns)
    bilanco_years = df_bilanco_pivot.columns.tolist()
    selected_bilanco_years = st.multiselect(
        "Görüntülenecek Yıllar (Bilanço)",
        bilanco_years,
        default=bilanco_years,
        key="trend_bilanco_years"
    )

    if selected_bilanco_years:
        base_year_bilanco = st.selectbox(
            "Baz Yıl (Bilanço)",
            selected_bilanco_years,
            key="trend_bilanco_base"
        )

        # Work on the selected columns
        df_bilanco_selected = df_bilanco_pivot[selected_bilanco_years].copy()
        df_bilanco_trend = df_bilanco_selected.copy()

        # For each financial item (row), compute the trend relative to the base year
        for idx in df_bilanco_trend.index:
            base_val = df_bilanco_selected.loc[idx, base_year_bilanco]
            if base_val != 0:
                df_bilanco_trend.loc[idx] = (df_bilanco_selected.loc[idx] / base_val) * 100
            else:
                df_bilanco_trend.loc[idx] = 0

        st.dataframe(df_bilanco_trend.style.format("{:.2f} %"))

    st.markdown("---")

    # ---- GELİR TABLOSU TREND ANALİZİ ----
    df_gelir = pd.read_excel("ing_income.xlsx")
    # Drop unnecessary column if exists
    if "Unnamed: 1" in df_gelir.columns:
        df_gelir = df_gelir.drop(columns=["Unnamed: 1"])
    df_gelir_pivot = df_gelir.set_index("Yıllar").T

    gelir_years = df_gelir_pivot.columns.tolist()
    selected_gelir_years = st.multiselect(
        "Görüntülenecek Yıllar (Gelir Tablosu)",
        gelir_years,
        default=gelir_years,
        key="trend_gelir_years"
    )

    if selected_gelir_years:
        base_year_gelir = st.selectbox(
            "Baz Yıl (Gelir Tablosu)",
            selected_gelir_years,
            key="trend_gelir_base"
        )

        df_gelir_selected = df_gelir_pivot[selected_gelir_years].copy()
        df_gelir_trend = df_gelir_selected.copy()

        for idx in df_gelir_trend.index:
            base_val = df_gelir_selected.loc[idx, base_year_gelir]
            if base_val != 0:
                df_gelir_trend.loc[idx] = (df_gelir_selected.loc[idx] / base_val) * 100
            else:
                df_gelir_trend.loc[idx] = 0

        st.dataframe(df_gelir_trend.style.format("{:.2f} %"))



def run_ratio_analysis_dashboard():
    st.subheader("📈 Rasyo Analizi")
    st.write("Rasyo analizlerinin gösterileceği alan.")
    st.markdown("### 🔑 Finansal Rasyolar")

    
    # Read Excel files
    df = pd.read_excel("ing_balance.xlsx")
    df2 = pd.read_excel("ing_income.xlsx")

    # Clean column names by stripping whitespace
    df.columns = df.columns.str.strip()
    df2.columns = df2.columns.str.strip()

    # Drop unnecessary column if exists
    if "Unnamed: 1" in df2.columns:
        df2 = df2.drop(columns=["Unnamed: 1"])

    # --- Compute ratios ---
    df["Faktoring/Maddi"] = df["Faktoring Alacakları"] / df["MADDİ DURAN VARLIKLAR (Net)"]
    df["Krediler/Finansal"] = df["KREDİLER (Net)"] / df["Finansal Varlıklar (Net)"]
    df["Nakit/Krediler"] = df["Nakit ve Nakit Benzerleri"] / df["KREDİLER (Net)"]

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    # --- KPI Metrics ---
    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Faktoring / Maddi Duran Varlıklar",
        f"{latest['Faktoring/Maddi']:.2f}",
        f"{latest['Faktoring/Maddi'] - previous['Faktoring/Maddi']:+.2f}"
    )
    col2.metric(
        "Krediler / Finansal Varlıklar",
        f"{latest['Krediler/Finansal']:.2f}",
        f"{latest['Krediler/Finansal'] - previous['Krediler/Finansal']:+.2f}"
    )
    col3.metric(
        "Nakit / Krediler",
        f"{latest['Nakit/Krediler']:.2f}",
        f"{latest['Nakit/Krediler'] - previous['Nakit/Krediler']:+.2f}"
    )

    # --- Ratio Charts Side-by-Side ---
    st.markdown("### 📈 Zaman İçindeki Değişim")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.plotly_chart(px.line(df, x="Yıllar", y="Faktoring/Maddi", title="Faktoring / Maddi Duran Varlıklar"), use_container_width=True)

    with chart_col2:
        st.plotly_chart(px.line(df, x="Yıllar", y="Krediler/Finansal", title="Krediler / Finansal Varlıklar"), use_container_width=True)

    st.plotly_chart(px.line(df, x="Yıllar", y="Nakit/Krediler", title="Nakit / Krediler"), use_container_width=True)

    # --- Data Table ---
    st.markdown("### 📊 Tüm Rasyo Verileri")
    st.dataframe(df[["Yıllar", "Faktoring/Maddi", "Krediler/Finansal", "Nakit/Krediler"]].style.format({
        "Faktoring/Maddi": "{:.2f}",
        "Krediler/Finansal": "{:.2f}",
        "Nakit/Krediler": "{:.2f}"
    }))

    
# 📝 Report builder module (modularized)
def run_report_builder():

    st.subheader("📝 Raporum")
    st.write("Rapor oluşturma alanı.")


    if "reports" not in st.session_state:
        st.session_state["reports"] = {}

    if "current_report" not in st.session_state:
        st.session_state["current_report"] = None

    # Create new report
    st.markdown("### 📄 Yeni Rapor Oluştur")
    new_report_name = st.text_input("Rapor Adı Girin", "")
    if st.button("Raporu Oluştur") and new_report_name:
        if new_report_name not in st.session_state["reports"]:
            st.session_state["reports"][new_report_name] = {
                "markdown": "",
                "charts": []
            }
            st.session_state["current_report"] = new_report_name

    report_names = list(st.session_state["reports"].keys())

    if report_names:
        selected = st.selectbox(
            "Rapor Seç", 
            report_names, 
            index=report_names.index(st.session_state["current_report"]) 
            if st.session_state["current_report"] in report_names 
            else 0
        )
        st.session_state["current_report"] = selected
        report = st.session_state["reports"][selected]

        st.markdown("### ✍️ Rapor İçeriği")
        report["markdown"] = st.text_area("Markdown İçeriği", value=report["markdown"], height=200)

        st.markdown("### 📊 Eklenmiş Grafikler")
        for i, fig in enumerate(report["charts"]):
            st.plotly_chart(fig, use_container_width=True)

        if st.button("PDF Olarak İndir"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Arial", size=12)

            html = markdown(report["markdown"])
            soup = BeautifulSoup(html, "html.parser")

            for element in soup.find_all():
                if element.name == "h1":
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(0, 10, element.text, ln=True)
                elif element.name == "h2":
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 10, element.text, ln=True)
                elif element.name == "li":
                    pdf.set_font("Arial", size=12)
                    pdf.cell(0, 10, f"- {element.text}", ln=True)
                elif element.name == "p":
                    pdf.set_font("Arial", size=12)
                    pdf.multi_cell(0, 10, element.text)
                pdf.ln(2)

            # Save charts as PNG images and insert
            with tempfile.TemporaryDirectory() as tmpdir:
                for i, fig in enumerate(report["charts"]):
                    image_path = os.path.join(tmpdir, f"chart_{i}.png")
                    try:
                        fig.update_layout(
                            template="plotly",
                            paper_bgcolor="white",
                            plot_bgcolor="white"
                        )
                        fig.write_image(image_path, format="png")
                        pdf.image(image_path, w=180)
                        pdf.ln(5)
                    except Exception as e:
                        st.warning(f"Grafik {i+1} PDF'e eklenemedi: {e}")

            pdf_output = pdf.output(dest="S").encode("latin-1")
            buffer = BytesIO(pdf_output)
            b64 = base64.b64encode(buffer.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="{selected}.pdf">📥 PDF\'i İndir</a>'
            st.markdown(href, unsafe_allow_html=True)

    else:
        st.info("Henüz oluşturulmuş bir rapor yok.")


def run_customer_segmentation():
    st.subheader("💳 Müşteri Segmentasyonu")
    st.write("Segmentasyon analiz alanı.")

def run_credit_model_training():
    st.subheader("💳 Model Eğitimi")
    st.write("Kredi skorlama model eğitimi alanı.")

def run_score_prediction():
    st.subheader("💳 Skor Tahmini")
    st.write("Skor tahminlerinin gösterileceği alan.")

def run_fraud_detection():
    st.subheader("🚨 Fraud")
    st.write("Fraud (anomalili işlem) analizlerinin yapılacağı alan.")

def run_product_matcher():
    st.subheader("🎯 Ürün Bul")
    st.write("Ürün eşleştirme algoritmalarının uygulanacağı alan.")

def run_housing_valuation():
    st.subheader("🏘️ Konut Fiyatlama")
    st.write("Konut fiyat tahmin modellerinin gösterileceği alan.")

def run_akbilmis_ai_assistant():
    st.subheader("🤖 AK Bilmiş")
    st.write("Akbank için bilgi veren yapay zeka asistanı.")

def run_macro_dashboard():
    st.subheader("📉 Makro Bankam")
    st.write("Makro ekonomik göstergelerin analiz edileceği alan.")



# 🟥 Sidebar — Full navigation with icons
st.sidebar.title("🔎 Navigasyon")
main_section = st.sidebar.radio("📂 Modül Seçin", [
    "📊 Tablolarım",
    "📈 Analizlerim",
    "📝 Raporum",
    "💳 Kredi Skorlama",
    "🚨 Fraud",
    "🎯 Ürün Bul",
    "🏘️ Konut Fiyatlama",
    "🤖 AK Bilmiş",
    "📉 Makro Bankam"
])



# 🟨 Modular Section Routing
if main_section == "📊 Tablolarım":

    sub_tab = st.sidebar.radio("Alt Sekmeler", ["Bilanço", "Gelir Tablosu"])
    st.markdown(f"#### {sub_tab}")

    if sub_tab == "Bilanço":
        df = pd.read_excel("ing_balance.xlsx")
        filtered_chart_section(df, key_prefix="bilanco")

    elif sub_tab == "Gelir Tablosu":
        df = pd.read_excel("ing_income.xlsx")
        if "Unnamed: 1" in df.columns:
            df = df.drop(columns=["Unnamed: 1"])
        filtered_chart_section(df, key_prefix="gelir")

elif main_section == "📈 Analizlerim":
    sub_tab = st.sidebar.radio("Alt Bölüm", [
        "Yüzde Analizi",
        "Trend",
        "Rasyo"
    ])
    if sub_tab == "Yüzde Analizi":
        run_common_size_analysis()
    elif sub_tab == "Trend":
        run_trend_analysis()
    elif sub_tab == "Rasyo":
        run_ratio_analysis_dashboard()

elif main_section == "📝 Raporum":
    run_report_builder()

elif main_section == "💳 Kredi Skorlama":
    run_credit_model_training()
    
elif main_section == "🚨 Fraud":
    run_fraud_detection()

elif main_section == "🎯 Ürün Bul":
    run_product_matcher()

elif main_section == "🏘️ Konut Fiyatlama":
    run_housing_valuation()

elif main_section == "🤖 AK Bilmiş":
    run_akbilmis_ai_assistant()

elif main_section == "📉 Makro Bankam":
    run_macro_dashboard()


