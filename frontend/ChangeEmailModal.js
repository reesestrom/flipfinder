window.ChangeEmailModal = function ChangeEmailModal({ currentEmail, onClose, onSave }) {
    const [newEmail, setNewEmail] = React.useState(currentEmail);
    const [error, setError] = React.useState("");
    
  
    async function handleSave() {
      if (!newEmail || newEmail === currentEmail) {
        onClose();
        return;
      }
      try {
        const res = await fetch("https://flipfinder.onrender.com/change_email", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ old_email: currentEmail, new_email: newEmail })
        });
  
        if (res.ok) {
          onSave(newEmail);
        } else {
          const err = await res.json();
          setError(err.detail || "Something went wrong");
        }
      } catch (e) {
        setError("Server error");
      }
    }
  
    return React.createElement("div", { className: "modal-overlay" },
        React.createElement("div", { className: "modal-content" },
          React.createElement("h3", null, "Change Email"),
          React.createElement("input", {
            className: "modal-input",
            value: newEmail,
            onChange: e => setNewEmail(e.target.value)
          }),
          error && React.createElement("div", { className: "modal-error" }, error),
          React.createElement("div", { style: { marginTop: "20px" } },
            React.createElement("button", {
              className: "save-schedule-btn",
              onClick: handleSave,
              style: { marginRight: "10px" }
            }, "Save"),
            React.createElement("button", {
              className: "close-schedule-btn",
              onClick: onClose
            }, "✕")
          )
        )
      );
      
  }
  