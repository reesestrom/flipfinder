window.FORCE_LOGIN_MODE = true;

ReactDOM.createRoot(document.getElementById("root")).render(
  React.createElement(App, { authOnly: false })
);
