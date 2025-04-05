window.DeleteAccountModal = function DeleteAccountModal({ email, onClose, onDelete }) {
    return React.createElement("div", { className: "modal-overlay" },
      React.createElement("div", { className: "modal-window" },
        React.createElement("h3", {
          style: {
            textAlign: "center",
            fontWeight: "600",
            marginBottom: "24px"
          }
        }, "Your Account and Information Will Be Permanently Deleted"),
  
        React.createElement("div", {
          style: {
            display: "flex",
            justifyContent: "center",
            gap: "12px"
          }
        },
          React.createElement("button", {
            onClick: onDelete,
            style: {
              backgroundColor: "#d32f2f",
              color: "#fff",
              border: "none",
              padding: "10px 24px",
              borderRadius: "12px",
              fontWeight: "bold",
              cursor: "pointer",
              fontSize: "16px"
            }
          }, "Delete"),
  
          React.createElement("button", {
            onClick: onClose,
            className: "modal-close-button"
          }, "X")
        )
      )
    );
  };
  