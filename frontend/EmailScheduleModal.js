window.EmailScheduleModal = function EmailScheduleModal({ username, selectedDays = [], onClose, onSave }) {
  const [days, setDays] = React.useState(() => new Set(selectedDays));
  const dayLabels = ["S", "M", "T", "W", "T", "F", "S"];

  // 🟢 Ensure days are hydrated from backend
  React.useEffect(() => {
    async function fetchDays() {
      try {
        const res = await fetch(`https://flipfinder.onrender.com/get_email_days/${username}`);
        const data = await res.json();
        console.log("✅ Fetched days from server:", data.days);
        if (Array.isArray(data.days)) {
          setDays(new Set(data.days));
        }
      } catch (err) {
        console.error("❌ Failed to fetch email days:", err);
      }
    }

    fetchDays();
  }, [username]);

  function toggleDay(day) {
    const newDays = new Set(days);
    newDays.has(day) ? newDays.delete(day) : newDays.add(day);
    setDays(newDays);
  }

  async function handleSave() {
    const toSave = Array.from(days);
    try {
      await fetch("https://flipfinder.onrender.com/set_email_days", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, days: toSave })
      });
      onSave(toSave);
    } catch (err) {
      alert("Failed to save email days.");
      console.error(err);
    }
  }

  return React.createElement("div", { className: "modal-overlay" },
    React.createElement("div", { className: "modal-content" },
      React.createElement("h3", null, "Select which days you want to receive emails"),
      React.createElement("div", { className: "days-grid" },
        dayLabels.map((label, i) =>
          React.createElement("button", {
            key: i,
            className: `day-button ${days.has(i) ? "selected" : ""}`,
            onClick: () => toggleDay(i)
          }, label)
        )
      ),
      React.createElement("button", { className: "save-schedule-btn", onClick: handleSave }, "Save"),
      React.createElement("button", { className: "close-schedule-btn", onClick: onClose }, "✕")
    )
  );
};
