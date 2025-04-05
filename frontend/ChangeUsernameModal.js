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

    React.createElement("button", {
      className: "account-option",
      onClick: () => window.handleOpenEmailSchedule && window.handleOpenEmailSchedule()
    }, "Change Email Schedule"),

    React.createElement("button", {
      className: "account-option",
      onClick: () => window.handleOpenUsernameModal && window.handleOpenUsernameModal()
    }, "Change Username"),

    React.createElement("button", { className: "account-option" }, "Change Email"),
    React.createElement("button", { className: "account-option" }, "Change Password"),
    React.createElement("button", { className: "account-option delete-account" }, "Delete Account")
  );
};
