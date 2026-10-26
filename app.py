import os
import streamlit as st
from datetime import datetime
from src.config import ensure_directories, DEFAULT_TZ
from src.ocr import extract_text, is_tesseract_available
from src.storage import load_memories, save_memory, image_path_for, delete_memory
from src.search import search_memories
from src.task_extraction import extract_tasks
from src.tasks_storage import load_tasks, save_tasks, update_task, set_completed, delete_task
from src.preferences import load_preferences, save_preferences
from src.briefing import get_daily_briefing, plan_tasks
from src.reminders import run_deadline_check, load_reminder_history
from src.qa import answer_question
from src.connections import related_memories

st.set_page_config(page_title="RecallFlow AI", page_icon="🧠", layout="wide")

def main():
    ensure_directories()

    st.title("🧠 RecallFlow AI — Smart Planner, QA & Connections")
    st.markdown("Your intelligent visual memory assistant with memory deletion, connections, grounded QA, smart planning, and task editing.")

    # Status check for Tesseract OCR
    ocr_ready = is_tesseract_available()
    if ocr_ready:
        st.sidebar.success("🟢 Tesseract OCR: Active & Ready")
    else:
        st.sidebar.warning("🟡 Tesseract OCR: Not detected (OCR will be skipped)")

    # Reminder Preferences (Sidebar)
    st.sidebar.markdown("---")
    st.sidebar.header("⏰ Reminder Preferences")
    prefs = load_preferences()
    
    with st.sidebar.form("prefs_form"):
        b_time = st.text_input("Daily Briefing Time", value=prefs.get("briefing_time", "08:00"))
        days_bef = st.number_input("Remind Days Before Deadline", min_value=0, max_value=7, value=prefs.get("days_before_deadline", 1))
        tz_input = st.text_input("Timezone", value=prefs.get("timezone", DEFAULT_TZ))
        save_prefs_btn = st.form_submit_button("Save Preferences")
        
        if save_prefs_btn:
            new_prefs = {
                "briefing_time": b_time,
                "days_before_deadline": days_bef,
                "timezone": tz_input
            }
            save_preferences(new_prefs)
            st.sidebar.success("Preferences saved!")
            st.rerun()

    # Sidebar for adding memory
    st.sidebar.markdown("---")
    st.sidebar.header("➕ Add New Memory")
    with st.sidebar.form("memory_form", clear_on_submit=True):
        uploaded_file = st.file_uploader("Upload Image (PNG, JPG)", type=["png", "jpg", "jpeg"])
        title = st.text_input("Title")
        description = st.text_area("Description / Notes")
        submit_btn = st.form_submit_button("Save Memory & Extract Tasks")

        if submit_btn:
            if uploaded_file is not None and title:
                temp_path = os.path.join("data", "temp_upload." + uploaded_file.name.split(".")[-1])
                os.makedirs("data", exist_ok=True)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                ocr_res = extract_text(temp_path)

                if os.path.exists(temp_path):
                    os.remove(temp_path)

                mem_record = save_memory(title, description, uploaded_file, ocr_res)
                
                extracted = extract_tasks(ocr_res)
                st.session_state["pending_tasks"] = extracted
                st.session_state["pending_memory_id"] = mem_record["id"]
                st.session_state["pending_image_filename"] = mem_record["image_path"]

                st.sidebar.success("Memory saved! Review extracted tasks below.")
                st.rerun()
            else:
                st.sidebar.error("Please provide an image and a title.")

    # Daily Briefing Section
    st.markdown("---")
    st.subheader("☀️ Daily Briefing")
    briefing = get_daily_briefing()
    
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    with col_b1:
        st.metric("🔥 Overdue", len(briefing.get("overdue", [])))
    with col_b2:
        st.metric("🎯 Due Today", len(briefing.get("due_today", [])))
    with col_b3:
        st.metric("⏳ Upcoming", len(briefing.get("upcoming", [])))
    with col_b4:
        st.metric("✅ Completed", len(briefing.get("completed", [])))

    if briefing.get("overdue") or briefing.get("due_today"):
        with st.expander("📌 View Priority Briefing Tasks", expanded=True):
            if briefing.get("overdue"):
                st.error("Overdue Tasks:")
                for t in briefing["overdue"]:
                    st.write(f"- {t.get('text')} (Due: {t.get('due_date')})")
            if briefing.get("due_today"):
                st.warning("Due Today:")
                for t in briefing["due_today"]:
                    st.write(f"- {t.get('text')}")

    # --- SMART DAILY PLAN SECTION ---
    st.markdown("---")
    st.subheader("🧭 Smart Daily Plan")
    st.caption("Recommended execution order based on urgency and priority (Medium = normal priority).")
    
    planned_tasks = plan_tasks()
    
    if not planned_tasks:
        st.info("No active tasks to plan. Add some tasks to see your smart schedule!")
    else:
        _PLAN_GROUP_ICON = {
            "🔥 Overdue": "🔴",
            "🎯 Due Today": "🟠",
            "⏳ Upcoming": "🟡",
            "📅 Later": "🔵",
            "📌 No Due Date": "⚪"
        }
        for pt in planned_tasks:
            group_hdr = pt.get("plan_group", "Task")
            icon = _PLAN_GROUP_ICON.get(group_hdr, "📌")
            prio_str = f"⚡ {str(pt.get('priority', 'normal')).upper()}"
            due_text = f"📅 Due: {pt.get('due_date')}" if pt.get('due_date') else "📅 No date"
            
            with st.container():
                st.markdown(f"{icon} **{pt.get('text')}**  \n`{prio_str}` • `{due_text}` • *Why here: {pt.get('plan_reason')}*")
            st.markdown("")

    # Deadline Check Trigger Button
    st.markdown("---")
    col_tr1, col_tr2 = st.columns([2, 1])
    with col_tr1:
        st.write("Trigger deadline checks manually or test reminder notifications.")
    with col_tr2:
        if st.button("🔔 Run Deadline Check Now"):
            res = run_deadline_check(dry_run=False)
            st.success(f"Check complete! Sent: {len(res['reminders_sent'])}, Skipped (deduplicated): {len(res['reminders_skipped'])}")

    # --- ASK YOUR MEMORIES SECTION (GROUNDED QA) ---
    st.markdown("---")
    st.subheader("💬 Ask Your Memories")
    st.caption("Ask questions about your saved screenshots and notes. Answers are strictly grounded in your saved records with verbatim evidence snippets.")

    qa_query = st.text_input("Ask a question (e.g., 'What was my assignment deadline?' or 'Find notes about python'):", key="qa_input_box")
    ask_clicked = st.button("Ask Memory")

    if ask_clicked and qa_query.strip():
        result = answer_question(qa_query)
        if result.no_results:
            st.info("❌ I couldn't find this in your saved memories.")
        else:
            st.success(f"Found {len(result.answers)} matching memory record(s):")
            if result.possible_conflict and result.message:
                st.warning(result.message)
                
            for ans in result.answers:
                with st.container():
                    col_q1, col_q2 = st.columns([1, 2])
                    with col_q1:
                        img_p = image_path_for(ans.memory)
                        if img_p and os.path.exists(img_p):
                            st.image(img_p, use_container_width=True)
                        else:
                            st.warning("Source image not found.")
                    with col_q2:
                        st.markdown(f"**{ans.memory.get('title', 'Untitled')}** *(Saved: {ans.memory.get('created_at', '')})*")
                        st.markdown("📌 **Evidence Snippets:**")
                        for match in ans.matches:
                            st.markdown(f"> *\"{match.snippet}\"*")
                            st.caption(f"Source field: {match.field_name}")
                    st.markdown("---")

    # --- MEMORY CONNECTIONS SECTION ---
    st.markdown("---")
    st.subheader("🔗 Memory Connections")
    st.caption("Explore related memories and linked tasks based on shared keywords and context.")

    memories_for_conn = load_memories()
    if not memories_for_conn:
        st.info("No memories saved yet. Add some memories to explore connections!")
    else:
        mem_options = {f"{m.get('title', 'Untitled')} ({m.get('created_at', '')})": m for m in memories_for_conn}
        selected_label = st.selectbox("Select a memory to find connections:", list(mem_options.keys()), key="conn_select_box")
        
        selected_mem = mem_options[selected_label]
        min_rel_score = st.slider("Minimum relevance score threshold", min_value=0.5, max_value=5.0, value=1.5, step=0.5, key="conn_slider")

        related = related_memories(selected_mem, memories_for_conn, min_score=min_rel_score)

        st.markdown(f"**Related Memories ({len(related)}) for: *{selected_mem.get('title', 'Untitled')}***")
        
        if not related:
            st.info("No strongly related memories found at this threshold. Try lowering the relevance threshold slider above.")
        else:
            for rel in related:
                with st.container():
                    col_c1, col_c2 = st.columns([1, 3])
                    with col_c1:
                        if rel.image_filename and os.path.exists(rel.image_filename):
                            st.image(rel.image_filename, use_container_width=True)
                        else:
                            st.warning("Image not found.")
                    with col_c2:
                        st.markdown(f"**{rel.title}** *(Saved: {rel.created_at})*")
                        st.caption(f"💡 **Why related:** {rel.reason}")
                        if rel.snippet:
                            st.markdown(f"> *\"{rel.snippet}\"*")
                            
                        with st.expander(f"Inspect memory & tasks: {rel.title}"):
                            linked_tasks = [t for t in load_tasks() if t.get("memory_id") == rel.memory_id]
                            if not linked_tasks:
                                st.caption("No tasks explicitly linked to this memory.")
                            else:
                                st.caption(f"Linked Tasks ({len(linked_tasks)}):")
                                for lt in linked_tasks:
                                    is_done = lt.get("completed", False)
                                    status_icon = "✅" if is_done else "⬜"
                                    st.markdown(f"- {status_icon} {lt.get('text')} *(Due: {lt.get('due_date', 'None')})*")
                st.markdown("---")

    # Task Review Section if pending tasks exist
    if "pending_tasks" in st.session_state and st.session_state["pending_tasks"]:
        st.markdown("---")
        st.subheader("📋 Review Extracted Tasks")
        st.info("We extracted these tasks from your uploaded image. Review, edit, or toggle them before saving.")

        pending_tasks = st.session_state["pending_tasks"]
        updated_tasks = []

        with st.form("task_review_form"):
            for i, task in enumerate(pending_tasks):
                st.markdown(f"**Task #{i+1}**")
                include = st.checkbox("Include this task", value=True, key=f"inc_{i}")
                t_text = st.text_input("Task Text", value=task.text, key=f"text_{i}")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    prio = st.selectbox("Priority", ["low", "medium", "high"], index=["low", "medium", "high"].index(task.priority), key=f"prio_{i}")
                with col_b:
                    date_val = st.date_input("Due Date (Optional)", value=datetime.strptime(task.due_date, "%Y-%m-%d").date() if task.due_date else None, key=f"date_{i}")

                if task.is_ambiguous_date:
                    st.warning(f"⚠️ Ambiguous date phrase detected: '{task.raw_date_phrase}'. Please set a concrete due date if needed.")

                if include:
                    updated_tasks.append({
                        "text": t_text,
                        "memory_id": st.session_state.get("pending_memory_id"),
                        "image_filename": st.session_state.get("pending_image_filename"),
                        "due_date": date_val.strftime("%Y-%m-%d") if date_val else None,
                        "priority": prio,
                        "provenance": "confirmed"
                    })
                st.markdown("---")

            save_confirmed_btn = st.form_submit_button("Save Confirmed Tasks")
            if save_confirmed_btn:
                if updated_tasks:
                    save_tasks(updated_tasks)
                    st.success(f"{len(updated_tasks)} tasks saved successfully!")
                del st.session_state["pending_tasks"]
                st.rerun()

    # Tasks Checklist Section with Edit & Delete
    st.markdown("---")
    st.subheader("✅ Your Tasks Checklist")
    all_tasks = load_tasks()

    if not all_tasks:
        st.info("No tasks saved yet. Upload an image containing a to-do list to extract tasks!")
    else:
        for t in all_tasks:
            t_id = t["id"]
            edit_key = f"editing_{t_id}"
            if edit_key not in st.session_state:
                st.session_state[edit_key] = False

            col_chk, col_txt, col_edit, col_del = st.columns([0.05, 0.75, 0.1, 0.1])
            
            with col_chk:
                checked = st.checkbox("", value=t.get("completed", False), key=f"chk_{t_id}")
                if checked != t.get("completed", False):
                    set_completed(t_id, checked)
                    st.rerun()
            with col_txt:
                style_open = "~~" if t.get("completed") else ""
                due_str = f" 📅 Due: {t.get('due_date')}" if t.get('due_date') else " 📅 no due date"
                prio_str = f" ⚡ {t.get('priority', 'normal').upper()}"
                st.markdown(f"{style_open}**{t.get('text')}**{style_open} `{prio_str}`{due_str}")
            with col_edit:
                if st.button("✏️", key=f"edit_btn_{t_id}", help="Edit Task"):
                    st.session_state[edit_key] = not st.session_state[edit_key]
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_{t_id}", help="Delete Task"):
                    delete_task(t_id)
                    if edit_key in st.session_state:
                        del st.session_state[edit_key]
                    st.rerun()

            # Inline Edit Form if toggled
            if st.session_state[edit_key]:
                with st.form(key=f"edit_form_{t_id}"):
                    st.markdown(f"**Edit Task Details:**")
                    new_text = st.text_input("Task Text", value=t.get("text", ""))
                    has_due = st.checkbox("Has a due date", value=bool(t.get("due_date")))
                    existing_date = datetime.strptime(t.get("due_date"), "%Y-%m-%d").date() if t.get("due_date") else datetime.now().date()
                    new_date = st.date_input("Due Date", value=existing_date)
                    
                    prio_options = ["low", "normal", "high"]
                    curr_prio = t.get("priority", "normal")
                    curr_idx = prio_options.index(curr_prio) if curr_prio in prio_options else 1
                    new_prio = st.selectbox("Priority", prio_options, index=curr_idx)

                    submit_edit = st.form_submit_button("Save Changes")
                    if submit_edit:
                        final_due = new_date.strftime("%Y-%m-%d") if has_due else None
                        update_task(t_id, text=new_text, due_date=final_due, priority=new_prio)
                        st.session_state[edit_key] = False
                        st.success("Task updated successfully!")
                        st.rerun()
                st.markdown("---")

    # Reminder History Section
    st.markdown("---")
    with st.expander("🕑 Local Reminder History"):
        history = load_reminder_history()
        if not history:
            st.info("No reminder history recorded yet. Click 'Run deadline check now' when tasks are due.")
        else:
            st.caption("Showing local reminder log entries (newest first). No external notifications sent.")
            for h in history:
                task_txt = h.get("text") or "(deleted task)"
                st.markdown(f"- **{task_txt}** — Reason: `{h.get('reason')}` (Due: {h.get('due_date')}) at *{h.get('notified_at')}*")

    # Search and Display Memories with Delete Action
    st.markdown("---")
    query = st.text_input("🔍 Search memories (titles, descriptions, and OCR text):", "")

    memories = load_memories()
    filtered_memories = search_memories(memories, query)

    st.subheader(f"Saved Memories ({len(filtered_memories)})")

    if not filtered_memories:
        st.info("No memories found. Upload your first memory using the sidebar!")
        return

    for mem in filtered_memories:
        mem_id = mem.get("id")
        with st.container():
            col1, col2 = st.columns([1, 2])
            with col1:
                img_full_path = image_path_for(mem)
                if img_full_path and os.path.exists(img_full_path):
                    st.image(img_full_path, use_container_width=True)
                else:
                    st.warning("Image file not found.")
            with col2:
                st.subheader(mem.get("title", "Untitled"))
                st.caption(f"Saved on: {mem.get('created_at', '')}")
                if mem.get("description"):
                    st.write(f"**Description:** {mem.get('description')}")
                
                with st.expander("📄 Extracted OCR Text"):
                    st.code(mem.get("ocr_text", "No text extracted."), language="text")

                # Delete memory confirmation flow inside each card
                del_state_key = f"confirm_del_mem_{mem_id}"
                if del_state_key not in st.session_state:
                    st.session_state[del_state_key] = False

                if not st.session_state[del_state_key]:
                    if st.button("🗑️ Delete memory", key=f"del_mem_btn_{mem_id}"):
                        st.session_state[del_state_key] = True
                        st.rerun()
                else:
                    st.warning("⚠️ Delete this memory? Associated tasks will be preserved.")
                    col_y, col_n = st.columns(2)
                    with col_y:
                        if st.button("Yes, delete", key=f"conf_del_mem_{mem_id}"):
                            delete_memory(mem_id)
                            st.session_state[del_state_key] = False
                            st.success("Memory deleted!")
                            st.rerun()
                    with col_n:
                        if st.button("Cancel", key=f"cancel_del_mem_{mem_id}"):
                            st.session_state[del_state_key] = False
                            st.rerun()

            st.markdown("---")

if __name__ == "__main__":
    main()