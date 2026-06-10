import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import time
import threading

# 1. إعدادات الصفحة والهوية البصرية
st.set_page_config(
    page_title="CPU Scheduler Simulator Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تخصيص المظهر بألوان عصرية عبر CSS خفيف لحواف البطاقات
st.markdown("""
    <style>
    .kpi-card {
        background-color: #252538;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #00F0FF;
        text-align: center;
    }
    .kpi-card-purple {
        background-color: #252538;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #8A2BE2;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# إدارة حالة المحاكاة داخل الـ Session State لمنع تضارب الـ Threads عند إعادة التحميل
if "simulation_running" not in st.session_state:
    st.session_state.simulation_running = False
if "stop_event" not in st.session_state:
    st.session_state.stop_event = threading.Event()

# 2. الشق الجانبي للتحكم والمدخلات (Sidebar)
st.sidebar.title("⚙️ Control Panel")
st.sidebar.markdown("---")

# اختيار الخوارزمية
algo_choice = st.sidebar.selectbox(
    "Choose Algorithm:",
    ["FCFS (First Come First Serve)", "SJF (Shortest Job First)"]
)

# تحديد سرعة المحاكاة
simulation_speed = st.sidebar.slider("Simulation Speed (Seconds per MS):", 0.1, 2.0, 0.5, step=0.1)

st.sidebar.markdown("### 📥 Processes Input")

default_data = pd.DataFrame([
    {"Process ID": "P1", "Arrival Time": 0, "Burst Time": 4},
    {"Process ID": "P2", "Arrival Time": 1, "Burst Time": 3},
    {"Process ID": "P3", "Arrival Time": 2, "Burst Time": 1},
    {"Process ID": "P4", "Arrival Time": 3, "Burst Time": 2},
])

edited_df = st.sidebar.data_editor(
    default_data, 
    num_rows="dynamic", 
    use_container_width=True,
    disabled=st.session_state.simulation_running # قفل الجدول أثناء التشغيل
)

# أزرار التحكم بالمحاكاة
if not st.session_state.simulation_running:
    run_button = st.sidebar.button("▶ RUN SIMULATION", use_container_width=True, type="primary")
    stop_button = False
else:
    run_button = False
    stop_button = st.sidebar.button("🛑 STOP SIMULATION", use_container_width=True, type="secondary")

# تفعيل زر الإيقاف فوراً عند الضغط عليه
if stop_button:
    st.session_state.stop_event.set()
    st.session_state.simulation_running = False
    st.rerun()

# 3. الواجهة الرئيسية للويب (Main Panel)
st.title("⚡ CPU SCHEDULER SIMULATOR PRO")
st.write("A modern web-based simulation tool for operating system CPU scheduling algorithms.")
st.markdown("---")

# دالة الجدولة والمحاكاة التي سيتم تشغيلها داخل الـ Thread المنفصل
def run_scheduling_logic(processes, algo, speed, stop_event, placeholders):
    status_p, kpi_p, chart_p = placeholders
    gantt_data = []
    waiting_times = {}
    turnaround_times = {}
    
    if "FCFS" in algo:
        order_pool = sorted(processes, key=lambda x: x["Arrival Time"])
    else:
        order_pool = [p.copy() for p in processes]

    current_time = 0
    
    while order_pool and not stop_event.is_set():
        if "FCFS" in algo:
            best_process = order_pool.pop(0)
            if current_time < best_process["Arrival Time"]:
                current_time = best_process["Arrival Time"]
        else:
            available_processes = [p for p in order_pool if p["Arrival Time"] <= current_time]
            if not available_processes:
                current_time = min(p["Arrival Time"] for p in order_pool)
                available_processes = [p for p in order_pool if p["Arrival Time"] <= current_time]
            best_process = min(available_processes, key=lambda x: x["Burst Time"])
            order_pool.remove(best_process)

        pid = best_process["Process ID"]
        arr = best_process["Arrival Time"]
        burst = best_process["Burst Time"]
        
        start_time = current_time
        waiting_times[pid] = start_time - arr
        
        # محاكاة نبضات المعالج والتنفيذ الفعلي بالوقت مع فحص الـ Thread Event
        for tick in range(1, burst + 1):
            if stop_event.is_set():
                return
            status_p.info(f"⏳ Running **{pid}**... (Progress: {tick}/{burst} ms) | Global Time: {start_time + tick} ms")
            time.sleep(speed)
        
        current_time += burst
        end_time = current_time
        turnaround_times[pid] = end_time - arr
        
        gantt_data.append((pid, start_time, burst))
        
        # تحديث مؤشرات الأداء الحالية ديناميكياً
        current_avg_wt = sum(waiting_times.values()) / len(waiting_times)
        current_avg_tat = sum(turnaround_times.values()) / len(turnaround_times)
        
        with kpi_p.container():
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f'<div class="kpi-card"><h3 style="color:#A0A0B8; margin:0;">Current Avg Waiting Time</h3><h1 style="color:#00F0FF; margin:10px 0 0 0;">{current_avg_wt:.2f} ms</h1></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="kpi-card-purple"><h3 style="color:#A0A0B8; margin:0;">Current Avg Turnaround Time</h3><h1 style="color:#8A2BE2; margin:10px 0 0 0;">{current_avg_tat:.2f} ms</h1></div>', unsafe_allow_html=True)

        # تحديث رسم مخطط غانت خطوة بخطوة
        fig, ax = plt.subplots(figsize=(10, 2.5), facecolor='#1E1E2E')
        ax.set_facecolor('#252538')
        colors = ["#00F0FF", "#8A2BE2", "#FF007F", "#39FF14", "#FF9933"]
        
        for i, (g_pid, g_start, g_duration) in enumerate(gantt_data):
            color = colors[i % len(colors)]
            ax.barh(y="CPU", width=g_duration, left=g_start, color=color, edgecolor="#1E1E2E", height=0.4)
            ax.text(g_start + g_duration/2, 0, g_pid, ha='center', va='center', color='black', weight='bold', fontsize=11)
        
        ax.tick_params(colors='white', labelsize=10)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#A0A0B8')
        ax.spines['bottom'].set_color('#A0A0B8')
        ax.grid(axis='x', color='#32324D', linestyle='--', alpha=0.5)
        
        chart_p.pyplot(fig)
        plt.close(fig)

    if not stop_event.is_set():
        status_p.success("🎉 Simulation Completed Successfully!")

# تشغيل السيناريو عند الضغط على زر البدء
if run_button:
    processes = edited_df.to_dict(orient="records")
    processes = [
        p for p in processes 
        if pd.notna(p.get("Process ID")) and pd.notna(p.get("Arrival Time")) and pd.notna(p.get("Burst Time"))
    ]
    
    if len(processes) == 0:
        st.error("Please add at least one valid process to simulate.")
    else:
        st.session_state.simulation_running = True
        st.session_state.stop_event.clear()
        
        # إنشاء الـ Placeholders
        status_placeholder = st.empty()
        kpi_placeholder = st.empty()
        chart_placeholder = st.empty()
        placeholders = (status_placeholder, kpi_placeholder, chart_placeholder)
        
        # إنشاء وإطلاق الـ Thread الخلفي
        simulation_thread = threading.Thread(
            target=run_scheduling_logic, 
            args=(processes, algo_choice, simulation_speed, st.session_state.stop_event, placeholders)
        )
        
        simulation_thread.start()
        simulation_thread.join() # مزامنة الـ Thread مع واجهة الويب
        
        st.session_state.simulation_running = False
        st.rerun()

elif not st.session_state.simulation_running:
    st.info("💡 Adjust processes in the sidebar table and click 'RUN SIMULATION' to start.")
