window.DeleteAccountModal = function DeleteAccountModal({ onClose, onConfirm }) {
    return React.createElement("div", { className: "modal-overlay" },
      React.createElement("div", { className: "modal-content" },
        React.createElement("h3", null, "Delete Account"),
        React.createElement("p", {
          style: { marginBottom: "20px", textAlign: "center" }
        }, "Your account and all associated information will be permanently deleted."),
  
        React.createElement("div", { style: { marginTop: "20px" } },
          React.createElement("button", {
            onClick: onConfirm,
            style: {
              backgroundColor: "#d32f2f",
              color: "#fff",
              border: "none",
              padding: "10px 24px",
              borderRadius: "12px",
              fontWeight: "bold",
              cursor: "pointer",
              fontSize: "16px",
              marginRight: "10px"
            }
          }, "Delete"),
          React.createElement("button", {
            className: "close-schedule-btn",
            onClick: onClose
          }, "✕")
        )
      )
    );
  };
  