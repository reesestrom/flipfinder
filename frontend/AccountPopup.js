window.AccountPopup = function AccountPopup({ onClose }) {
    const popupRef = React.useRef(null);
  
    React.useEffect(() => {
      function handleClickOutside(event) {
        if (popupRef.current && !popupRef.current.contains(event.target)) {
          onClose();
        }
      }
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [onClose]);
  
    return React.createElement("div", { className: "account-popup", ref: popupRef },
      React.createElement("h4", { className: "account-title" }, "Account Settings"),
  
      // ✅ Change Email Schedule (already works)
      React.createElement("button", {
        className: "account-option",
        onClick: () => window.handleOpenEmailSchedule && window.handleOpenEmailSchedule()
      }, "Change Email Schedule"),
  
      React.createElement("button", {
        className: "account-option",
        onClick: () => {
          console.log("✅ Username button clicked");
          if (window.handleOpenUsernameModal) {
            window.handleOpenUsernameModal();
          } else {
            console.error("❌ handleOpenUsernameModal not available");
          }
        }
      }, "Change Username"),
      
  
      React.createElement("button", {
        className: "account-option",
        onClick: () => window.handleOpenEmailModal && window.handleOpenEmailModal()
      }, "Change Email"),
      React.createElement("button", {
        className: "account-option",
        onClick: () => window.handleOpenPasswordModal && window.handleOpenPasswordModal()
      }, "Change Password"),
      React.createElement("button", {
        className: "account-option delete-account",
        onClick: () => window.handleOpenDeleteModal && window.handleOpenDeleteModal()
      }, "Delete Account")
      
    );
  };
  