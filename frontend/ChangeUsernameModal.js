window.ChangeUsernameModal = function ChangeUsernameModal({ currentUsername, onClose, onSave }) {
  const [username, setUsername] = React.useState(currentUsername);
  const [error, setError] = React.useState("");

  async function handleSave() {
    setError("");
    const res = await fetch("https://flipfinder.onrender.com/change_username", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ old_username: currentUsername, new_username: username })
    });
    const data = await res.json();

    if (!res.ok) {
      setError(data.detail || "Unknown error");
    } else {
      onSave(username);
    }
  }

  return React.createElement("div", { className: "modal-overlay" },
    React.createElement("div", { className: "modal-content" },
      React.createElement("h3", null, "Change Your Username"),
      React.createElement("input", {
        type: "text",
        value: username,
        onChange: (e) => setUsername(e.target.value),
        className: "input-box"
      }),
      error && React.createElement("div", { className: "error-text" }, error),
      React.createElement("button", { className: "save-schedule-btn", onClick: handleSave }, "Save"),
      React.createElement("button", { className: "close-schedule-btn", onClick: onClose }, "✕")
    )
  );
};
