window.ChangePasswordModal = function ChangePasswordModal({ userEmail, onClose }) {
    const [status, setStatus] = React.useState("Sending...");
  
    console.log(userEmail)
    console.log("this is after^")
    
    React.useEffect(() => {
      async function sendReset() {
        try {
            const res = await fetch("https://flipfinder.onrender.com/request_password_reset", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: userEmail })
              });              
          const data = await res.json();
          if (res.ok) {
            setStatus(`An email with instructions has been sent to ${userEmail}`);
          } else {
            setStatus(data.detail || "Error sending email");
          }
        } catch (err) {
          console.error(err);
          setStatus("Error sending email");
        }
      }
  
      sendReset();
    }, [userEmail]);
  
    return React.createElement("div", { className: "modal-overlay" },
        React.createElement("div", { className: "modal-content" },
          React.createElement("h3", null, "Reset Your Password"),
          React.createElement("p", {
            style: { marginBottom: "20px", textAlign: "center" }
          }, `An email will be sent to ${userEmail} with instructions to reset your password.`),
      
          React.createElement("div", { style: { marginTop: "20px" } },
            React.createElement("button", {
              className: "save-schedule-btn",
              onClick: async () => {
                console.log("📨 Sending reset email to:", userEmail, typeof userEmail);
                try {
                  const res = await fetch("https://flipfinder.onrender.com/request_password_reset", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: userEmail })
                  });
                  const data = await res.json();
                  //alert(res.ok ? "✅ Reset email sent!" : data.message || "Something went wrong.");
                  onClose();
                } catch (err) {
                  alert("Something went wrong. Please try again later.");
                  onClose();
                }
              },
              style: { marginRight: "10px" }
            }, "Send"),
            React.createElement("button", {
              className: "close-schedule-btn",
              onClick: onClose
            }, "✕")
          )
        )
      );      
  }
  