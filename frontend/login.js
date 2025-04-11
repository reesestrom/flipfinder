const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  React.createElement(App, { authOnly: false }) // forces login/signup view
);