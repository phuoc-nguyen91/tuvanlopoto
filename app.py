import streamlit as st
import pandas as pd
import re
import google.generativeai as genai

# --- PHẦN 1: CẤU HÌNH TRANG WEB ---
st.set_page_config(page_title="Công Cụ Tư Vấn Lốp Xe Linglong", layout="wide")

# --- PHẦN 1.5: CẤU HÌNH API AN TOÀN VỚI STREAMLIT SECRETS ---
# LƯU Ý: Để sử dụng, bạn cần thêm API Key của Google vào Streamlit Secrets
# Tạo một file secrets.toml trong thư mục .streamlit với nội dung:
# google_api_key = "API_KEY_CUA_BAN"
api_configured = False
try:
    if 'google_api_key' in st.secrets:
        genai.configure(api_key=st.secrets["google_api_key"])
        api_configured = True
except Exception as e:
    # In ra lỗi để dễ dàng debug nếu có sự cố
    print(f"Lỗi cấu hình API: {e}")

# --- PHẦN 2: TẢI VÀ XỬ LÝ DỮ LIỆU ---
@st.cache_data
def load_tire_data():
    """
    Hàm này có nhiệm vụ tải và xử lý tất cả dữ liệu cần thiết cho ứng dụng,
    bao gồm bảng giá, mã gai và thông tin lốp theo xe.
    """
    try:
        # Tải các file dữ liệu chính
        df_prices_raw = pd.read_csv('BẢNG GIÁ BÁN LẺ_19_05_2025.csv', dtype=str)
        df_magai_raw = pd.read_csv('Mã Gai LINGLONG.csv', dtype=str)
        
        # Tải các file dữ liệu bổ sung về lốp theo xe
        df_xe_lop_1 = pd.read_csv('xe, đời xe,lop theo xe.........xls - Tyre-1.csv', dtype=str)
        df_xe_lop_2 = pd.read_csv('xe, đời xe,lop theo xe.........xls - tyre bổ sung.csv', dtype=str)
        
        # Hợp nhất hai file thông tin lốp theo xe
        df_lop_theo_xe = pd.concat([df_xe_lop_1, df_xe_lop_2], ignore_index=True)
        # Loại bỏ các dòng trùng lặp nếu có
        df_lop_theo_xe.drop_duplicates(inplace=True)

        # XỬ LÝ BẢNG GIÁ
        price_cols = ['stt', 'quy_cach', 'ma_gai', 'gia_ban_le', 'XUẤT XỨ']
        df_prices = df_prices_raw.iloc[:, :len(price_cols)]
        df_prices.columns = price_cols
        
        if 'gia_ban_le' in df_prices.columns:
            # Chuyển đổi cột giá sang dạng số, xử lý các ký tự không phải số
            df_prices['gia_ban_le'] = pd.to_numeric(
                df_prices['gia_ban_le'].str.replace(r'[^\d]', '', regex=True), 
                errors='coerce'
            )
            df_prices.dropna(subset=['gia_ban_le'], inplace=True)

        # XỬ LÝ MÔ TẢ MÃ GAI
        magai_cols = ['ma_gai', 'nhu_cau', 'ung_dung_cu_the', 'uu_diem_cot_loi', 'link_hinh_anh']
        df_magai = df_magai_raw.iloc[:, :len(magai_cols)]
        df_magai.columns = magai_cols
        
        # KẾT HỢP DỮ LIỆU GIÁ VÀ MÃ GAI
        df_master = pd.merge(df_prices, df_magai, on='ma_gai', how='left')

        # Điền và làm sạch dữ liệu
        for col in ['nhu_cau', 'ung_dung_cu_the', 'uu_diem_cot_loi', 'link_hinh_anh', 'XUẤT XỨ']:
            if col not in df_master.columns:
                df_master[col] = 'Chưa có thông tin'
            df_master[col] = df_master[col].fillna('Chưa có thông tin')

        for col in df_master.columns:
             if df_master[col].dtype == 'object':
                df_master[col] = df_master[col].str.strip()
        
        # Tạo cột 'base_size' để dễ dàng tìm kiếm theo kích thước cơ bản
        df_master['base_size'] = df_master['quy_cach'].str.split(' ').str[0]

        return df_master, df_lop_theo_xe

    except FileNotFoundError as e:
        st.error(f"Lỗi không tìm thấy file: **{e.filename}**. Vui lòng kiểm tra lại tên file và đảm bảo file đã được tải lên.")
        return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi đọc hoặc xử lý file: {e}")
        return pd.DataFrame(), pd.DataFrame()


# --- PHẦN 3: KHỞI TẠO VÀ CHẠY ỨNG DỤNG ---
df_master, df_lop_theo_xe = load_tire_data()

st.title("️🚗 BỘ CÔNG CỤ TƯ VẤN LỐP XE LINGLONG")
st.markdown("Xây dựng bởi **Chuyên Gia Lốp Thầm Lặng** - Dành cho những lựa chọn sáng suốt.")

# Kiểm tra xem dữ liệu đã được tải thành công chưa
if df_master.empty:
    st.warning("Không thể khởi động ứng dụng do lỗi tải dữ liệu. Vui lòng kiểm tra lại thông báo lỗi ở trên.")
else:
    # Tạo các tab cho các công cụ khác nhau
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
            
            # Sắp xếp kết quả theo giá bán để khách hàng dễ so sánh
            if 'gia_ban_le' in results.columns:
                results = results.sort_values(by="gia_ban_le")

            st.write("---")
            st.subheader(f"Kết quả tra cứu cho \"{search_term}\"")
            
            if not results.empty:
                st.success(f"Đã tìm thấy **{len(results)}** sản phẩm phù hợp.")
                
                # Hiển thị kết quả một cách trực quan
                for index, row in results.iterrows():
                    price_str = f"{row['gia_ban_le']:,} VNĐ" if pd.notna(row['gia_ban_le']) else "Chưa có giá"
                    col_title, col_price = st.columns([3, 1])
                    with col_title:
                        st.markdown(f"#### {row['quy_cach']} / **{row['ma_gai']}** (Xuất xứ: *{row['XUẤT XỨ']}*)")
                    with col_price:
                        st.markdown(f"<div style='text-align: right; font-size: 1.2em; color: #28a745; font-weight: bold;'>{price_str}</div>", unsafe_allow_html=True)
                    st.markdown(f"**👍 Ưu điểm cốt lõi:** {row['uu_diem_cot_loi']}")
                    
                    # Hiển thị báo giá khuyến mãi nếu có giá
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

                # Thông tin liên hệ và kêu gọi hành động (Call To Action)
                st.markdown("##### **Để được tư vấn và báo giá tốt nhất, vui lòng liên hệ:**")
                col_cta_1, col_cta_2 = st.columns([2,1])
                with col_cta_1:
                    st.markdown("📞 **HOTLINE:** **0943 24 24 24**")
                    st.markdown("💬 **Zalo:** [https://zalo.me/0943242424](https://zalo.me/0943242424)")
                    st.markdown("📍 **Địa chỉ:** 114 Đường Số 2, Trường Thọ, Thủ Đức, TPHCM")
                with col_cta_2:
                    try:
                        st.image("qr.jpg", width=150, caption="Quét mã để kết bạn Zalo")
                    except Exception:
                        st.info("Không tìm thấy file qr.jpg")
                st.markdown("<hr style='border: 2px solid #ff4b4b; border-radius: 5px;'/>", unsafe_allow_html=True)
            else:
                st.warning("Không tìm thấy sản phẩm nào phù hợp với kích thước bạn đã nhập.")
        else:
            st.info("Vui lòng chọn một kích thước lốp từ danh sách ở trên để bắt đầu tra cứu.")

    # --- Công cụ 2: Chatbot AI Nâng Cao ---
    with tab_chatbot:
        st.header("Trợ Lý AI Tư Vấn Lốp Xe Chuyên Sâu")

        if not api_configured:
            st.error("Tính năng Chatbot yêu cầu API Key của Google. Vui lòng cấu hình trong Streamlit Secrets để sử dụng.")
        else:
            # Khởi tạo mô hình và lịch sử chat nếu chưa có
            model = genai.GenerativeModel('gemini-1.5-pro-latest')
            if "chat_session" not in st.session_state:
                # --- SYSTEM PROMPT ĐÃ ĐƯỢC NÂNG CẤP HOÀN TOÀN ---
                # Đây là "bộ não" của Chatbot, chứa đựng tất cả kiến thức và chiến lược bán hàng.
                system_prompt = (
                    "**BỐI CẢNH:** Bạn là một chuyên gia tư vấn bán hàng cấp cao, am hiểu sâu sắc về sản phẩm lốp xe Linglong tại thị trường Việt Nam. Bạn đang chat với khách hàng qua Messenger. Mục tiêu cuối cùng là chốt đơn hoặc lấy được thông tin liên hệ của khách hàng."
                    "\n\n"
                    "**PHONG CÁCH:** Luôn chuyên nghiệp, thân thiện, kiên nhẫn và đáng tin cậy. Sử dụng ngôn ngữ tự nhiên, dễ hiểu."
                    "\n\n"
                    "**CHIẾN LƯỢC TƯ VẤN (CỰC KỲ QUAN TRỌNG):**"
                    "\n1.  **Luôn ưu tiên 'Sản xuất tại Thái Lan':** Khi tư vấn, hãy luôn làm nổi bật các sản phẩm có xuất xứ Thái Lan. Đây là lợi thế cạnh tranh cốt lõi để xây dựng niềm tin. Ví dụ: 'Dạ với size này, em xin giới thiệu mẫu ... được sản xuất tại nhà máy Linglong Thái Lan, chất lượng rất tốt và được khách hàng bên em ưa chuộng ạ.'"
                    "\n2.  **Sử dụng 'Bằng Chứng Chất Lượng' để thuyết phục:** Khi khách hỏi về chất lượng hoặc so sánh, BẮT BUỘC phải đề cập đến các điểm sau:"
                    "\n    * **Đối tác OEM uy tín:** 'Lốp Linglong được các hãng xe lớn như Volkswagen, BMW, Ford, và General Motors tin tưởng chọn làm lốp theo xe (OEM), đây là bảo chứng tốt nhất cho chất lượng toàn cầu của hãng.'"
                    "\n    * **Chứng nhận quốc tế:** 'Sản phẩm của Linglong đạt đủ các chứng nhận chất lượng khắt khe như DOT (Mỹ), ECE (Châu Âu).'"
                    "\n    * **Chính sách bảo hành:** 'Bên em có chính sách bảo hành chính hãng 5 năm cho lốp Linglong nên anh/chị hoàn toàn yên tâm về độ bền ạ.'"
                    "\n3.  **Xử lý khéo léo vấn đề 'Nguồn gốc Trung Quốc':** Nếu khách e ngại, hãy trả lời theo kịch bản: 'Dạ em hiểu băn khoăn của anh/chị. Linglong là một thương hiệu toàn cầu. Để đáp ứng tốt nhất thị trường Việt Nam, hãng tập trung vào các dòng sản phẩm sản xuất tại nhà máy công nghệ cao ở Thái Lan, đảm bảo chất lượng vượt trội. Chất lượng này đã được các hãng xe lớn như BMW, VW kiểm chứng khi lắp cho xe mới của họ.'"
                    "\n4.  **So sánh thông minh với đối thủ:**"
                    "\n    * **vs. Michelin/Bridgestone:** 'Dạ so với các thương hiệu cao cấp như Michelin, Linglong mang lại trải nghiệm vận hành và độ an toàn tương đương nhưng với mức giá hợp lý hơn rất nhiều. Đây là lựa chọn rất kinh tế và thông minh ạ.'"
                    "\n    * **vs. Kenda/Advenza:** 'Dạ so với các thương hiệu cùng phân khúc, Linglong nổi trội hơn hẳn về công nghệ và độ tin cậy do được sản xuất tại Thái Lan và là đối tác OEM cho nhiều hãng xe lớn trên thế giới.'"
                    "\n\n"
                    "**DỮ LIỆU SẢN PHẨM VÀ KHUYẾN MÃI:**"
                    f"\n- **Bảng giá và thông tin chi tiết sản phẩm:**\n{df_master.to_string()}\n"
                    f"\n- **Thông tin lốp theo xe (dùng để tham khảo khi khách hỏi xe A đi lốp nào):**\n{df_lop_theo_xe.to_string()}\n"
                    "\n- **Chương trình khuyến mãi hiện tại:** Mua 2 lốp giảm 5% trên tổng hóa đơn. Mua 4 lốp giảm 10% trên tổng hóa đơn."
                    "\n\n"
                    "**KẾT THÚC CUỘC TRÒ CHUYỆN (BẮT BUỘC):**"
                    "\nLuôn kết thúc bằng việc kêu gọi hành động. Hãy chủ động xin số điện thoại để tư vấn kỹ hơn hoặc mời khách hàng đến cửa hàng."
                    "\n- **Mẫu 1 (Xin SĐT):** 'Để em có thể tư vấn chính xác và báo giá lăn bánh tốt nhất cho mình, anh/chị có thể cho em xin số điện thoại được không ạ?'"
                    "\n- **Mẫu 2 (Mời đến cửa hàng):** 'Nếu có thời gian, em mời anh/chị ghé qua cửa hàng bên em tại 114 Đường Số 2, Trường Thọ, Thủ Đức, TPHCM để xem lốp trực tiếp và được hỗ trợ tốt nhất ạ.'"
                )
                
                # Bắt đầu phiên chat với prompt hệ thống và lời chào mở đầu
                st.session_state.chat_session = model.start_chat(history=[
                    {"role": "user", "parts": [system_prompt]}, 
                    {"role": "model", "parts": ["Chào bạn, tôi là Trợ lý AI của Lốp Xe Linglong. Tôi có thể giúp gì cho bạn ngay hôm nay ạ?"]}
                ])

            # Hiển thị lịch sử chat (bỏ qua prompt hệ thống)
            for message in st.session_state.chat_session.history[1:]: 
                with st.chat_message(name="assistant" if message.role == "model" else "user"):
                    st.markdown(message.parts[0].text)

            # Ô nhập liệu của người dùng
            if prompt := st.chat_input("Nhập câu hỏi của khách hàng vào đây..."):
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.spinner("Trợ lý AI đang soạn câu trả lời..."):
                    # Gửi câu hỏi của người dùng và nhận câu trả lời từ mô hình
                    response = st.session_state.chat_session.send_message(prompt)
                    with st.chat_message("assistant"):
                        st.markdown(response.text)


    # --- Công cụ 3: Tính chi phí ---
    with tab_cost:
        st.header("Ước tính chi phí sử dụng lốp trên mỗi Kilômét")
        
        col1_cost, col2_cost = st.columns(2)
        with col1_cost:
            gia_lop = st.number_input("Nhập giá 1 lốp xe (VNĐ):", min_value=0, step=100000)
            tuoi_tho = st.number_input("Tuổi thọ dự kiến của lốp (km):", min_value=10000, step=5000, value=45000, 
                                     help="Thông thường, lốp xe du lịch đi được từ 40,000 km đến 70,000 km.")
        with col2_cost:
            st.write("")
            st.write("")
            if gia_lop > 0 and tuoi_tho > 0:
                chi_phi_per_km = gia_lop / tuoi_tho
                st.metric(label="CHI PHÍ ƯỚC TÍNH MỖI KM", 
                          value=f"{chi_phi_per_km:,.2f} VNĐ / km",
                          help="Chi phí này chỉ mang tính tham khảo và có thể thay đổi tùy điều kiện vận hành.")
            else:
                st.info("Nhập giá và tuổi thọ dự kiến để xem chi phí ước tính.")

