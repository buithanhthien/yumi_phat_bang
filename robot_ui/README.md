# Giao diện robot Yumi — ROS 2 Jazzy

## Khởi chạy

Mở UI chưa bật phần cứng. Bấm Bật Nav2 và RViz để bật phần cứng còn thiếu cùng Nav2.

```bash
source /home/khoaiuh/yumi_phat_bang/setup_yumi.bash
python3 /home/khoaiuh/yumi_phat_bang/robot_ui/startup_layout.py
```

UI và các tiến trình con dùng workspace Yumi với thư mục `install`.
Cần Python hệ thống, PyQt6, PyYAML và các package ROS/Nav2 trong Jazzy.
Cấu hình nằm trong `robot_config.json`.

## Nav2 và bản đồ

Bấm Bật Nav2 và RViz để chạy Nav2 với `start_robot:=true`; UI nhận diện các node/topic đang có để tránh bật trùng phần cứng. Nhóm EKF hoặc xử lý LiDAR đang chạy thiếu node phải được dừng trước khi bật lại. Tắt Nav2 cũng dọn phần cứng do phiên UI này bật; phần cứng chạy ngoài UI vẫn được giữ.
Bấm Tạo bản đồ rồi bắt đầu để chạy SLAM với `start_robot:=false`.
Tắt Nav2 trước khi tạo bản đồ; kết thúc SLAM trước khi bật Nav2.
UI chỉ dọn nhóm tiến trình do chính nó khởi chạy.

Khi map_server có sẵn, UI đọc tham số yaml_filename để nhận diện bản đồ. Khi chưa có map_server, dùng bản đồ đã chọn
hoặc mặc định X5_19102026.yaml, trùng mặc định launch Nav2 Yumi hiện tại.

Tải bản đồ khi Nav2 đang hoạt động gọi /map_server/load_map. Phải hủy
mục tiêu đang chạy trước. Chỉ lưu lựa chọn sau khi dịch vụ báo thành công.
Sau khi đổi bản đồ, đặt lại vị trí ban đầu trong RViz trước khi điều hướng.
Nếu Nav2 chưa bật, lựa chọn được lưu cho lần bật kế tiếp.
Không tự thay keepout mask cũ; cần kiểm tra mask phù hợp với bản đồ được chọn.

Waypoint và lộ trình cũ được giữ nguyên. Chỉ hiển thị/chạy điểm thuộc đúng
tên bản đồ; không chuyển tọa độ cũ sang bản đồ mới bằng cách đổi tên.

## DỪNG

DỪNG hủy hàng đợi và mục tiêu Nav2, kể cả mục tiêu RViz thông qua dịch vụ
hủy action. Không gửi khóa emergency_stop, không sửa firmware và không khóa
PS2. PS2 tiếp quản theo watchdog hiện có của STM32 sau khi ROS ngừng điều khiển.
Cho phép chạy lại mở chọn hành trình mới; không tiếp tục hành trình đã hủy.
Tắt Nav2 và RViz là thao tác riêng với nhóm tiến trình UI sở hữu.

## Kiểm tra

Đã kiểm tra cú pháp và khởi tạo Qt offscreen trong ROS domain riêng:
cập nhật trạng thái, DỪNG và Cho phép chạy lại.
Đã thử nút Bật/Tắt với hai LiDAR thật, EKF và Agent hệ thống có sẵn.
Bài thử dùng Qt offscreen nên bỏ cửa sổ RViz và không gửi mục tiêu Nav2.

## Hội thoại tiếng Việt

Khung chat trên màn hình chính nhận văn bản hoặc giọng nói. Bấm **Mic** để
thu, rồi bấm **Gửi giọng nói** để gửi. Phiên thu tự kết thúc sau tối đa 60 giây.
Robot tự đọc câu trả lời. RobotEyes đếm lại 10 giây sau khi phiên hội thoại
hoàn tất, theo các điều kiện chờ hiện có.

Ví dụ lệnh: `Đi tới phòng X5.4`, `Chạy lộ trình tuần tra`, `Dừng lại`.
Waypoint và lộ trình phải thuộc bản đồ đang dùng. Xác nhận đích trên màn hình
trước khi di chuyển. Lệnh Dừng lại yêu cầu hủy điều hướng Nav2 giống nút **DỪNG**.

Cài các gói trong `requirements.txt` vào môi trường Python đang chạy UI.
Nhận dạng tiếng Việt dùng các tệp GIPFormer của Zackon trong
`~/.cache/gipformer` (có thể đặt `YUMI_GIPFORMER_DIR`). Supertonic 3 dùng
mô hình có sẵn trong bộ nhớ đệm của Supertonic, cùng với `aplay` từ
`alsa-utils`. Audio dùng thiết bị mặc định. Có thể đặt `YUMI_MIC_DEVICE`
(chỉ số thiết bị PyAudio) và `YUMI_SPEAKER_DEVICE` (tên thiết bị ALSA).

Lưu khóa OpenAI tại `/home/khoaiuh/yumi_phat_bang/openai.key`, một dòng chứa
khóa. File có quyền `0600` và được loại khỏi Git. Mở file bằng trình
soạn thảo cục bộ để nhập khóa. Mặc định UI dùng `gpt-6-luna` với mức suy luận `none`. Có thể chọn model khác qua `YUMI_OPENAI_MODEL`. ChatGPT nhận văn bản hội thoại. Nhận dạng
giọng nói và tổng hợp tiếng Việt chạy trên mini PC.
