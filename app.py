import streamlit as st
import pandas as pd
import re
import pypdf # Streamlit Cloud đã có sẵn thư viện này

# --- PHẦN 1: XỬ LÝ VÀ TẢI DỮ LIỆU ---
# (Phần code này sẽ được streamlit cache lại để chạy nhanh hơn)
@st.cache_data
def load_data():
    """
    Hàm này sẽ tải, xử lý và kết hợp tất cả các file dữ liệu.
    Streamlit sẽ lưu kết quả vào cache để không phải chạy lại mỗi lần người dùng tương tác.
    """
    # --- Hàm con để xử lý file Bảng giá PDF ---
    def parse_price_pdf(file_path):
        try:
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                full_text = "".join(page.extract_text() for page in reader.pages)
        except FileNotFoundError:
            st.error(f"Lỗi: Không tìm thấy file {file_path}. Vui lòng đảm bảo file này nằm cùng thư mục với file app.py")
            return pd.DataFrame()

        # Dùng regex để tìm các dòng dữ liệu hợp lệ
        # Mẫu regex tìm: (số),"(quy cách)","(mã gai)","(xuất xứ)","(giá)"
        # Regex được cải tiến để xử lý các dòng bị ngắt
        pattern = re.compile(r'\"(\d+)\s*\",\"(.*?)\s*\",\"(.*?)\s*\",\"(.*?)\s*\",\"([\d,]+?)\s*\"', re.DOTALL)
        matches = pattern.findall(full_text)
        
        if not matches:
             st.error("Không thể trích xuất dữ liệu từ file PDF. Vui lòng kiểm tra định dạng file Bảng giá.")
             return pd.DataFrame()

        df = pd.DataFrame(matches, columns=['stt', 'quy_cach', 'ma_gai', 'xuat_xu', 'gia_ban_le'])
        
        # Dọn dẹp dữ liệu
        df['gia_ban_le'] = df['gia_ban_le'].str.replace(',', '').astype(float)
        df['quy_cach'] = df['quy_cach'].str.strip()
        df['ma_gai'] = df['ma_gai'].str.strip()
        df['xuat_xu'] = df['xuat_xu'].str.strip()
        return df

    # --- Tải các file CSV ---
    try:
        df_prices = parse_price_pdf('BẢNG GIÁ BÁN LẺ_19_05_2025 - bảng giá bán lẻ TL.pdf')
        
        df_magai = pd.read_csv('Mã Gai LINGLONG - Mã Gai.csv')
        # Đổi tên cột một cách an toàn
        df_magai.columns = ['ma_gai', 'mo_ta_gai', 'nhu_cau'][:len(df_magai.columns)]
        df_magai['ma_gai'] = df_magai['ma_gai'].str.strip()

        df_xe1 = pd.read_csv('xe, đời xe,lop theo xe.........xls - Tyre-1.csv')
        df_xe2 = pd.read_csv('xe, đời xe,lop theo xe.........xls - tyre bổ sung.csv')
        df_xe = pd.concat([df_xe1, df_xe2], ignore_index=True)
        # Đổi tên cột một cách an toàn
        df_xe.columns = ['hang_xe', 'mau_xe', 'doi_xe', 'quy_cach'][:len(df_xe.columns)]
        df_xe.dropna(subset=['hang_xe', 'mau_xe', 'quy_cach'], inplace=True)
        df_xe['quy_cach'] = df_xe['quy_cach'].str.strip()
        df_xe['display_name'] = df_xe['hang_xe'] + " " + df_xe['mau_xe']


    except FileNotFoundError as e:
        st.error(f"Lỗi: Không tìm thấy file dữ liệu - {e.filename}. Vui lòng kiểm tra lại.")
        return pd.DataFrame(), pd.DataFrame()

    # --- Kết hợp dữ liệu ---
    df_master = pd.merge(df_prices, df_magai, on='ma_gai', how='left')
    df_master['nhu_cau'] = df_master['nhu_cau'].fillna('Tiêu chuẩn')
    df_master['mo_ta_gai'] = df_master['mo_ta_gai'].fillna('Gai lốp tiêu chuẩn của Linglong.')
    
    return df_master, df_xe

# Tải dữ liệu khi ứng dụng khởi động
df_master, df_xe = load_data()


# --- PHẦN 2: XÂY DỰNG GIAO DIỆN NGƯỜI DÙNG (UI) ---

st.set_page_config(page_title="Công Cụ Tư Vấn Lốp Xe", layout="wide")

# Tiêu đề chính của ứng dụng
st.title("️🚗 BỘ CÔNG CỤ TƯ VẤN LỐP XE LINGLONG")
st.markdown("Xây dựng bởi **Chuyên Gia Lốp Thầm Lặng** - Dành cho những lựa chọn sáng suốt.")

# Nếu không tải được dữ liệu thì dừng lại
if df_master.empty or df_xe.empty:
    st.warning("Không thể khởi động ứng dụng do lỗi tải dữ liệu. Vui lòng kiểm tra lại các file.")
else:
    # Tạo các Tab để chuyển đổi giữa 2 công cụ
    tab1, tab2 = st.tabs(["**⚙️ Công Cụ Tư Vấn Lốp Xe**", "**🧮 Công Cụ Tính Chi Phí Lốp**"])

    # --- Giao diện cho Tab 1: Tư vấn lốp ---
    with tab1:
        st.header("Tìm lốp Linglong phù hợp với xe của bạn")
        
        col1, col2, col3 = st.columns(3)

        with col1:
            # 1. Chọn hãng xe
            hang_xe_list = sorted(df_xe['hang_xe'].unique())
            selected_hang_xe = st.selectbox("1. Chọn Hãng Xe:", hang_xe_list)

        with col2:
            # 2. Chọn mẫu xe (danh sách sẽ tự cập nhật theo hãng xe)
            mau_xe_list = sorted(df_xe[df_xe['hang_xe'] == selected_hang_xe]['mau_xe'].unique())
            selected_mau_xe = st.selectbox("2. Chọn Mẫu Xe:", mau_xe_list)

        # Lấy quy cách lốp tương ứng
        lop_theo_xe_series = df_xe[(df_xe['hang_xe'] == selected_hang_xe) & (df_xe['mau_xe'] == selected_mau_xe)]['quy_cach']
        
        if not lop_theo_xe_series.empty:
            lop_theo_xe = lop_theo_xe_series.iloc[0]
            with col3:
                 st.text_input("3. Kích thước lốp theo xe:", value=lop_theo_xe, disabled=True)
            
            # 4. Chọn nhu cầu sử dụng
            nhu_cau_list = sorted(df_master['nhu_cau'].unique())
            selected_nhu_cau = st.selectbox("4. Chọn nhu cầu chính của bạn:", nhu_cau_list, help="Êm ái, Tiết kiệm, Thể thao hay Đa dụng?")

            # 5. Nút tìm kiếm
            if st.button("🔍 Tìm Lốp Ngay", type="primary"):
                # Lọc kết quả
                results = df_master[(df_master['quy_cach'] == lop_theo_xe) & (df_master['nhu_cau'] == selected_nhu_cau)]
                
                st.success(f"Đã tìm thấy **{len(results)}** loại lốp phù hợp cho xe **{selected_hang_xe} {selected_mau_xe}** với kích thước **{lop_theo_xe}**.")

                if not results.empty:
                    for index, row in results.iterrows():
                        with st.expander(f"**Mã gai: {row['ma_gai']}** - Giá: {row['gia_ban_le']:,} VNĐ", expanded=True):
                            st.markdown(f"**- Mô tả:** {row['mo_ta_gai']}")
                            st.markdown(f"**- Nhu cầu:** {row['nhu_cau']}")
                            st.markdown(f"**- Xuất xứ:** {row['xuat_xu'].title()}")
                            st.markdown(f"---")
                else:
                    st.warning("Rất tiếc, không tìm thấy lốp Linglong nào khớp chính xác với lựa chọn này. Thử chọn nhu cầu 'Tiêu chuẩn' xem sao nhé!")
        else:
            st.info("Vui lòng chọn xe và nhu cầu rồi nhấn nút 'Tìm Lốp Ngay'.")

    # --- Giao diện cho Tab 2: Tính chi phí lốp ---
    with tab2:
        st.header("Ước tính chi phí sử dụng lốp trên mỗi Kilômét")
        
        col1_cost, col2_cost = st.columns(2)

        with col1_cost:
            gia_lop = st.number_input("Nhập giá 1 lốp xe (VNĐ):", min_value=0, step=100000)
            tuoi_tho = st.number_input("Tuổi thọ dự kiến của lốp (km):", min_value=10000, step=5000, value=45000, 
                                     help="Thông thường, lốp xe đi được từ 40,000 km đến 70,000 km tùy loại và điều kiện sử dụng.")

        if gia_lop > 0 and tuoi_tho > 0:
            chi_phi_per_km = gia_lop / tuoi_tho
            with col2_cost:
                st.metric(label="CHI PHÍ ƯỚC TÍNH MỖI KM", 
                          value=f"{chi_phi_per_km:,.2f} VNĐ / km",
                          help="Chi phí này chỉ mang tính tham khảo, không bao gồm các chi phí lắp đặt, cân bằng động...")
        else:
            with col2_cost:
                st.info("Nhập giá và tuổi thọ dự kiến để xem chi phí.")
