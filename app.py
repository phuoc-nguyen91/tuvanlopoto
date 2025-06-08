import streamlit as st
import pandas as pd
import re

# --- PHẦN CẤU HÌNH TRANG ---
# SỬA LỖI: Lệnh st.set_page_config phải được gọi đầu tiên để tránh lỗi
st.set_page_config(page_title="Công Cụ Tư Vấn Lốp Xe", layout="wide")

# --- PHẦN 1: XỬ LÝ VÀ TẢI DỮ LIỆU ---
@st.cache_data
def load_data():
    """
    Hàm này sẽ tải, xử lý và kết hợp tất cả các file dữ liệu.
    Streamlit sẽ lưu kết quả vào cache để không phải chạy lại mỗi lần người dùng tương tác.
    """
    try:
        # --- SỬA LỖI: Đọc tất cả các cột dưới dạng văn bản (string) để tránh lỗi kiểu dữ liệu ---
        df_prices = pd.read_csv('BẢNG GIÁ BÁN LẺ_19_05_2025.csv', dtype=str)
        
        # Gán tên cột một cách an toàn để tránh lỗi "Length mismatch"
        price_cols = ['stt', 'quy_cach', 'ma_gai', 'xuat_xu', 'gia_ban_le']
        df_prices.columns = price_cols[:len(df_prices.columns)]
        
        # Kiểm tra và dọn dẹp dữ liệu giá nếu cột tồn tại
        if 'gia_ban_le' in df_prices.columns:
            # Thay thế các ký tự không phải số và chuyển thành dạng số
            df_prices['gia_ban_le'] = pd.to_numeric(df_prices['gia_ban_le'].str.replace(r'[^\d]', '', regex=True), errors='coerce')
            df_prices.dropna(subset=['gia_ban_le'], inplace=True)
        
        # Dọn dẹp các cột khác
        if 'quy_cach' in df_prices.columns:
            df_prices['quy_cach'] = df_prices['quy_cach'].str.strip()
        if 'ma_gai' in df_prices.columns:
            df_prices['ma_gai'] = df_prices['ma_gai'].str.strip()
        if 'xuat_xu' in df_prices.columns:
            df_prices['xuat_xu'] = df_prices['xuat_xu'].str.strip()

        # --- SỬA LỖI: Đọc tất cả các cột dưới dạng văn bản (string) ---
        df_magai = pd.read_csv('Mã Gai LINGLONG - Mã Gai.csv', dtype=str)
        expected_cols = ['ma_gai', 'mo_ta_gai', 'nhu_cau']
        num_cols_to_use = min(len(df_magai.columns), len(expected_cols))
        df_magai = df_magai.iloc[:, :num_cols_to_use]
        df_magai.columns = expected_cols[:num_cols_to_use]
        df_magai['ma_gai'] = df_magai['ma_gai'].str.strip()

        # --- SỬA LỖI: Đọc tất cả các cột dưới dạng văn bản (string) ---
        df_xe1 = pd.read_csv('Tyre1.csv', dtype=str)
        df_xe2 = pd.read_csv('tyre_bosung.csv', dtype=str)
        df_xe = pd.concat([df_xe1, df_xe2], ignore_index=True)
        df_xe.columns = ['hang_xe', 'mau_xe', 'doi_xe', 'quy_cach'][:len(df_xe.columns)]
        df_xe.dropna(subset=['hang_xe', 'mau_xe', 'quy_cach'], inplace=True)
        df_xe['quy_cach'] = df_xe['quy_cach'].str.strip()
        df_xe['display_name'] = df_xe['hang_xe'] + " " + df_xe['mau_xe']

    except FileNotFoundError as e:
        st.error(f"Lỗi: Không tìm thấy file dữ liệu - {e.filename}. Vui lòng kiểm tra lại.")
        return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi đọc file dữ liệu: {e}")
        return pd.DataFrame(), pd.DataFrame()

    # --- Kết hợp dữ liệu ---
    df_master = pd.merge(df_prices, df_magai, on='ma_gai', how='left')
    
    # Điền các giá trị còn trống nếu có
    if 'nhu_cau' not in df_master.columns:
        df_master['nhu_cau'] = 'Tiêu chuẩn'
    else:
        df_master['nhu_cau'] = df_master['nhu_cau'].fillna('Tiêu chuẩn')
    
    if 'mo_ta_gai' not in df_master.columns:
        df_master['mo_ta_gai'] = 'Gai lốp tiêu chuẩn của Linglong.'
    else:
        df_master['mo_ta_gai'] = df_master['mo_ta_gai'].fillna('Gai lốp tiêu chuẩn của Linglong.')
    
    return df_master, df_xe

# Tải dữ liệu khi ứng dụng khởi động
df_master, df_xe = load_data()


# --- PHẦN 2: XÂY DỰNG GIAO DIỆN NGƯỜI DÙNG (UI) ---

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
