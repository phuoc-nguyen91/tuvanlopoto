import streamlit as st
import pandas as pd
import re
import google.generativeai as genai

# --- PHẦN 1: CẤU HÌNH TRANG WEB ---
st.set_page_config(page_title="Công Cụ Tra Cứu Lốp Xe", layout="wide")

# --- PHẦN 1.5: CẤU HÌNH API AN TOÀN VỚI STREAMLIT SECRETS ---
api_configured = False
try:
    if 'google_api_key' in st.secrets:
        genai.configure(api_key=st.secrets["google_api_key"])
        api_configured = True
except Exception as e:
    print(f"Lỗi cấu hình API: {e}")


# --- PHẦN 2: TẢI VÀ XỬ LÝ DỮ LIỆU ---
@st.cache_data
def load_tire_data():
    """
    Hàm này có nhiệm vụ tải và xử lý dữ liệu lốp từ các file CSV.
    """
    try:
        df_prices_raw = pd.read_csv('BẢNG GIÁ BÁN LẺ_19_05_2025.csv', dtype=str)
        df_magai_raw = pd.read_csv('Mã Gai LINGLONG.csv', dtype=str)

        # XỬ LÝ BẢNG GIÁ
        price_cols = ['stt', 'quy_cach', 'ma_gai', 'gia_ban_le']
        df_prices = df_prices_raw.iloc[:, :len(price_cols)]
        df_prices.columns = price_cols
        
        if 'gia_ban_le' in df_prices.columns:
            df_prices['gia_ban_le'] = pd.to_numeric(
                df_prices['gia_ban_le'].str.replace(r'[^\d]', '', regex=True), 
                errors='coerce'
            )
            df_prices.dropna(subset=['gia_ban_le'], inplace=True)

        # XỬ LÝ MÔ TẢ MÃ GAI
        magai_cols = ['ma_gai', 'nhu_cau', 'ung_dung_cu_the', 'uu_diem_cot_loi', 'link_hinh_anh']
        df_magai = df_magai_raw.iloc[:, :len(magai_cols)]
        df_magai.columns = magai_cols
        
        # KẾT HỢP DỮ LIỆU
        df_master = pd.merge(df_prices, df_magai, on='ma_gai', how='left')

        # Điền và làm sạch dữ liệu
        for col in ['nhu_cau', 'ung_dung_cu_the', 'uu_diem_cot_loi', 'link_hinh_anh']:
            if col not in df_master.columns:
                df_master[col] = 'Chưa có thông tin'
            df_master[col] = df_master[col].fillna('Chưa có thông tin')

        for col in df_master.columns:
             if df_master[col].dtype == 'object':
                df_master[col] = df_master[col].str.strip()
        
        df_master['base_size'] = df_master['quy_cach'].str.split(' ').str[0]

        return df_master

    except FileNotFoundError as e:
        st.error(f"Lỗi không tìm thấy file: **{e.filename}**. Vui lòng kiểm tra lại tên file.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi đọc file: {e}")
        return pd.DataFrame()


# --- PHẦN 3: KHỞI TẠO VÀ CHẠY ỨNG DỤNG ---
df_master = load_tire_data()

st.title("️🚗 BỘ CÔNG CỤ TƯ VẤN LỐP XE LINGLONG")
st.markdown("Xây dựng bởi **Chuyên Gia Lốp Thầm Lặng** - Dành cho những lựa chọn sáng suốt.")

if df_master.empty:
    st.warning("Không thể khởi động ứng dụng do lỗi tải dữ liệu. Vui lòng kiểm tra lại thông báo lỗi ở trên.")
else:
    # THÊM TÍNH NĂNG: Thêm Tab Chatbot
    tab_search, tab_chatbot, tab_cost = st.tabs([
        "**🔍 Tra Cứu Lốp Theo Size**", 
        "**🤖 Chat Với Trợ Lý AI**",
        "**🧮 Tính Chi Phí Lốp**"
    ])

    # --- Công cụ 1: Tra cứu giá theo size ---
    with tab_search:
        st.header("Tra cứu lốp Linglong theo kích thước")
        
        unique_sizes = sorted(df_master['base_size'].dropna().unique())
        options = ["--- Chọn hoặc tìm size lốp ---"] + unique_sizes
        
        size_query = st.selectbox(
            "Chọn kích thước lốp bạn muốn tìm:", 
            options=options,
            help="Bạn có thể gõ để tìm kiếm size trong danh sách."
        )

        if size_query != "--- Chọn hoặc tìm size lốp ---":
            search_term = size_query
            results = df_master[df_master['base_size'] == search_term].copy()
            
            if 'gia_ban_le' in results.columns:
                results = results.sort_values(by="gia_ban_le")

            st.write("---")
            st.subheader(f"Kết quả tra cứu cho \"{search_term}\"")
            
            if not results.empty:
                st.success(f"Đã tìm thấy **{len(results)}** sản phẩm phù hợp.")
                
                for index, row in results.iterrows():
                    price_str = f"{row['gia_ban_le']:,} VNĐ" if pd.notna(row['gia_ban_le']) else "Chưa có giá"
                    col_title, col_price = st.columns([3, 1])
                    with col_title:
                        st.markdown(f"#### {row['quy_cach']} / {row['ma_gai']}")
                    with col_price:
                        st.markdown(f"<div style='text-align: right; font-size: 1.2em; color: #28a745; font-weight: bold;'>{price_str}</div>", unsafe_allow_html=True)
                    st.markdown(f"**👍 Ưu điểm cốt lõi:** {row['uu_diem_cot_loi']}")
                    if pd.notna(row['gia_ban_le']):
                        with st.container():
                            st.markdown("🎁 **Báo giá khuyến mãi:**")
                            price_for_2 = (row['gia_ban_le'] * 2) * 0.95
                            price_for_4 = (row['gia_ban_le'] * 4) * 0.90
                            promo_col1, promo_col2 = st.columns(2)
                            with promo_col1:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;• Mua 2 lốp (giảm 5%): **<span style='color: #ff4b4b;'>{price_for_2:,.0f} VNĐ</span>**", unsafe_allow_html=True)
                            with promo_col2:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;• Mua 4 lốp (giảm 10%): **<span style='color: #ff4b4b;'>{price_for_4:,.0f} VNĐ</span>**", unsafe_allow_html=True)
                    st.markdown("---")

                st.markdown("##### **Để được tư vấn và báo giá tốt nhất, vui lòng liên hệ:**")
                col_cta_1, col_cta_2 = st.columns([2,1])
                with col_cta_1:
                    st.markdown("📞 **HOTLINE:** **0943 24 24 24**")
                    st.markdown("💬 **Zalo:** [https://zalo.me/0943242424](https://zalo.me/0943242424)")
                    st.markdown("📍 **Địa chỉ:** 114 Đường Số 2, Trường Thọ, Thủ Đức, TPHCM")
                with col_cta_2:
                    try:
                        st.image("qr.jpg", width=150, caption="Quét mã để kết bạn Zalo")
                    except Exception as e:
                        st.info("Không tìm thấy file qr.jpg")
                st.markdown("<hr style='border: 2px solid #ff4b4b; border-radius: 5px;'/>", unsafe_allow_html=True)
            else:
                st.warning("Không tìm thấy sản phẩm nào phù hợp với kích thước bạn đã nhập.")
        else:
            st.info("Vui lòng chọn một kích thước lốp từ danh sách ở trên để bắt đầu tra cứu.")

    # --- Công cụ 2: Chatbot ---
    with tab_chatbot:
        st.header("Trợ Lý AI Tư Vấn Lốp Xe")

        if not api_configured:
            st.warning("Tính năng Chatbot yêu cầu API Key. Vui lòng cấu hình trong Streamlit Secrets để sử dụng.")
        else:
            # Khởi tạo mô hình và lịch sử chat
            model = genai.GenerativeModel('gemini-1.5-pro-latest')
            if "chat_session" not in st.session_state:
                # Cung cấp "bộ não" cho chatbot
                system_prompt = (
                    "Bạn là một chuyên gia tư vấn bán hàng cho thương hiệu lốp xe Linglong tại Việt Nam. "
                    "Nhiệm vụ của bạn là trả lời các câu hỏi của khách hàng, tư vấn sản phẩm phù hợp và thuyết phục họ mua hàng. "
                    "Hãy luôn giữ thái độ thân thiện, chuyên nghiệp và đáng tin cậy. "
                    "Luôn kết thúc cuộc trò chuyện bằng cách xin số điện thoại hoặc mời khách hàng đến cửa hàng tại '114 Đường Số 2, Trường Thọ, Thủ Đức, TPHCM'. "
                    "Sử dụng dữ liệu sản phẩm sau đây để trả lời các câu hỏi về giá, mã gai và khuyến mãi:\n\n"
                    f"{df_master.to_string()}\n\n"
                    "Chương trình khuyến mãi hiện tại là: Mua 2 lốp giảm 5%, mua 4 lốp giảm 10%."
                )
                st.session_state.chat_session = model.start_chat(history=[{"role": "user", "parts": [system_prompt]}, {"role": "model", "parts": ["Chào bạn, tôi là trợ lý ảo của Lốp Xe Linglong. Tôi có thể giúp gì cho bạn hôm nay?"]}])

            # Hiển thị lịch sử chat
            for message in st.session_state.chat_session.history[1:]: # Bỏ qua system prompt
                with st.chat_message(name="assistant" if message.role == "model" else "user"):
                    st.markdown(message.parts[0].text)

            # Ô nhập liệu của người dùng
            if prompt := st.chat_input("Hỏi về sản phẩm, giá cả, khuyến mãi..."):
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.spinner("Trợ lý AI đang soạn câu trả lời..."):
                    response = st.session_state.chat_session.send_message(prompt)
                    with st.chat_message("assistant"):
                        st.markdown(response.text)


    # --- Công cụ 3: Tính chi phí ---
    with tab_cost:
        st.header("Ước tính chi phí sử dụng lốp trên mỗi Kilômét")
        
        col1_cost, col_cost = st.columns(2)
        with col1_cost:
            gia_lop = st.number_input("Nhập giá 1 lốp xe (VNĐ):", min_value=0, step=100000)
            tuoi_tho = st.number_input("Tuổi thọ dự kiến của lốp (km):", min_value=10000, step=5000, value=45000, 
                                     help="Thông thường, lốp xe đi được từ 40,000 km đến 70,000 km.")
        with col_cost:
            if gia_lop > 0 and tuoi_tho > 0:
                chi_phi_per_km = gia_lop / tuoi_tho
                st.metric(label="CHI PHÍ ƯỚC TÍNH MỖI KM", 
                          value=f"{chi_phi_per_km:,.2f} VNĐ / km",
                          help="Chi phí này chỉ mang tính tham khảo.")
            else:
                st.info("Nhập giá và tuổi thọ dự kiến để xem chi phí.")
