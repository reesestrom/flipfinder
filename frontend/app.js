// Full Flip Finder app with login and post-login search functionality
const { useState, useEffect } = React;
const [autoSearches, setAutoSearches] = useState([]);

function App() {
  const [searchInputs, setSearchInputs] = useState([""]);
  const [results, setResults] = useState([]);
  const [parsedQueries, setParsedQueries] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [username, setUsername] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userZip, setUserZip] = useState("");
  const [userPreferences, setUserPreferences] = useState([]);
  const [showPaywall, setShowPaywall] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [signupData, setSignupData] = useState({ username: "", email: "", password: "" });
  const [signupMessage, setSignupMessage] = useState("");
  const [loginData, setLoginData] = useState({ email: "", password: "" });
  const [loginMessage, setLoginMessage] = useState("");
  const [savedItems, setSavedItems] = useState([]);
  const [listingsSearched, setListingsSearched] = useState(0);
  



  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    const storedPrefs = localStorage.getItem("userPreferences");
    const storedZip = localStorage.getItem("zip");
  
    if (storedUser) {
      setUsername(storedUser);
      setIsAuthenticated(true);
      setUserPreferences(JSON.parse(storedPrefs || "[]"));
    }
  
    if (storedZip) {
      setUserZip(storedZip);
    } else {
      // ✅ Try to detect ZIP via geolocation and store it
      fetchZipFromLocation()
        .then(zip => {
          if (zip) {
            setUserZip(zip);
            localStorage.setItem("zip", zip);
          }
        })
        .catch(err => console.warn("Could not get ZIP from geolocation:", err));
    }
  }, []);
  
  

  async function handleSignupSubmit(e) {
    e.preventDefault();
    try {
      const res = await fetch("https://flipfinder.onrender.com/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(signupData)
      });
      const data = await res.json();
      if (res.ok) {
        setUsername(signupData.username);
        setIsAuthenticated(true);
        localStorage.setItem("user", signupData.username);
        localStorage.setItem("userPreferences", JSON.stringify(userPreferences));
        setSignupMessage("Signup successful!");
      } else {
        setSignupMessage(data.detail || "Signup failed");
      }
    } catch (error) {
      setSignupMessage("An error occurred during signup.");
    }
  }

  async function fetchZipFromLocation() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject("Geolocation not supported");
        return;
      }
  
      navigator.geolocation.getCurrentPosition(async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const response = await fetch(
            `https://api.opencagedata.com/geocode/v1/json?q=${latitude}+${longitude}&key=${process.env.REACT_APP_OPENCAGE_KEY}`
          );
          const data = await response.json();
          const zip = data?.results?.[0]?.components?.postcode;
          resolve(zip || null);
        } catch (err) {
          reject(err);
        }
      }, reject);
    });
  }
  

  async function handleLoginSubmit(e) {
    e.preventDefault();
    try {
      const res = await fetch("https://flipfinder.onrender.com/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(loginData)
      });
      const data = await res.json();
      if (res.ok) {
        setUsername(data.username);
        setIsAuthenticated(true);
        localStorage.setItem("user", data.username);
        // ⬇️ Fetch auto-searches
        fetch(`https://flipfinder.onrender.com/user_auto_searches/${data.username}`)
          .then(res => res.json())
          .then(searches => {
            const enabled = searches
              .filter(s => s.auto_search_enabled)
              .map(s => s.query_text);
            setAutoSearches(enabled);
          })
          .catch(err => console.error("Failed to load auto searches:", err));
  
        // ⬇️ Fetch saved listings for this user and store in state
        fetch(`https://flipfinder.onrender.com/saved_items/${data.username}`)
          .then(res => res.json())
          .then(items => setSavedItems(items))
          .catch(err => console.error("Failed to load saved items after login:", err));
      } else {
        setLoginMessage(data.detail || "Login failed");
      }
    } catch (error) {
      setLoginMessage("An error occurred during login.");
    }
  }
  
  async function toggleSaveItem(item) {
    const alreadySaved = savedItems.some(i => i.url === item.url);
    const updated = alreadySaved
      ? savedItems.filter(i => i.url !== item.url)
      : [...savedItems, item];
  
    setSavedItems(updated);
  
    try {
      await fetch("https://flipfinder.onrender.com/save_item", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, item })
      });
    } catch (err) {
      console.error("Failed to save item:", err);
    }
  }
  
  

  function handleLogOut() {
    setUsername("");
    setIsAuthenticated(false);
    localStorage.removeItem("user");
    localStorage.removeItem("userPreferences");
  }

  function handleSelectPreference(pref) {
    if (searchInputs.length >= 3 && !isSubscribed) {
      setShowPaywall(true);
      return;
    }
    setSearchInputs(prev => [...prev, pref]);
  }

  function handleInputChange(index, value) {
    const newInputs = [...searchInputs];
    newInputs[index] = value;
    setSearchInputs(newInputs);
  }

  function addSearchField() {
    if (searchInputs.length >= 3 && !isSubscribed) {
      setShowPaywall(true);
      return;
    }
    setSearchInputs([...searchInputs, ""]);
  }

  function removeSearchField(index) {
    const newInputs = [...searchInputs];
    newInputs.splice(index, 1);
    setSearchInputs(newInputs);
  }

  async function handleSearch() {
  setIsLoading(true);
  setResults([]);
  setParsedQueries([]);
  setListingsSearched(0);

  const evtSource = new EventSource("https://flipfinder.onrender.com/events");
  evtSource.onmessage = function (event) {
    if (event.data === "increment") {
      setListingsSearched(prev => prev + 1);
    }
  };

  let allResults = [];
  let parsedSet = [];

  try {
    for (let i = 0; i < searchInputs.length; i++) {
      const query = searchInputs[i];
      const res = await fetch("https://flipfinder.onrender.com/ai_search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          search: query,
          postalCode: userZip || "10001"
        })
      });

      if (!res.ok) throw new Error("Search failed");

      const data = await res.json();
      const parsed = data.parsed;
      const results = data.results.map(r => ({ ...r, _parsed: parsed }));

      allResults = [...allResults, ...results];
      parsedSet = [...parsedSet, parsed];
      setResults([...allResults]);
      setParsedQueries([...parsedSet]);

      await new Promise(resolve => setTimeout(resolve, 0));
    }
  } catch (error) {
    alert("Error performing one of the searches.");
    console.error("Search error:", error);
  } finally {
    evtSource.close(); // ✅ Clean up
    setIsLoading(false);
  }
}

  
  

  if (!isAuthenticated) {
    return React.createElement("div", {
      style: {
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#f7f7f7",
        padding: "20px"
      }
    },
      React.createElement("img", {
        src: "assets/flip finder logo.png",
        alt: "Flip Finder Logo",
        style: {
          width: "150px",
          marginBottom: "20px"
        }
      }),
      React.createElement("h2", null, "Welcome to Flip Finder"),
      React.createElement("form", { onSubmit: handleLoginSubmit, style: { maxWidth: "300px", width: "100%" } },
        ["email", "password"].map((field) =>
          React.createElement("div", { key: field, style: { marginBottom: "10px" } },
            React.createElement("input", {
              type: field === "password" ? "password" : "text",
              placeholder: field.charAt(0).toUpperCase() + field.slice(1),
              value: loginData[field],
              required: true,
              onChange: e => setLoginData({ ...loginData, [field]: e.target.value }),
              style: {
                width: "100%",
                padding: "10px",
                fontSize: "16px",
                border: "1px solid #ccc",
                borderRadius: "8px"
              }
            })
          )
        ),
        React.createElement("button", { type: "submit", className: "buttonPrimary", style: { width: "100%", padding: "10px" } }, "Log In"),
        loginMessage && React.createElement("p", null, loginMessage)
      ),
      React.createElement("div", { style: { marginTop: "20px" } },
        React.createElement("h4", null, "Don't have an account?"),
        React.createElement("form", { onSubmit: handleSignupSubmit, style: { maxWidth: "300px", width: "100%" } },
          ["username", "email", "password"].map((field) =>
            React.createElement("div", { key: field, style: { marginBottom: "10px" } },
              React.createElement("input", {
                type: field === "password" ? "password" : "text",
                placeholder: field.charAt(0).toUpperCase() + field.slice(1),
                value: signupData[field],
                required: true,
                onChange: e => setSignupData({ ...signupData, [field]: e.target.value }),
                style: {
                  width: "100%",
                  padding: "10px",
                  fontSize: "16px",
                  border: "1px solid #ccc",
                  borderRadius: "8px"
                }
              })
            )
          ),
          React.createElement("button", { type: "submit", className: "buttonSecondary", style: { width: "100%", padding: "10px" } }, "Sign Up"),
          signupMessage && React.createElement("p", null, signupMessage)
        )
      )
    );
  }

  return React.createElement("div", { style: { maxWidth: "800px", margin: "auto", padding: "20px" } },
    React.createElement("div", { className: "logo-wrapper" },
      React.createElement("img", {
        src: "assets/flip finder logo.png",
        alt: "Flip Finder Logo",
        height: "120"
      })
    ),
    React.createElement("div", { id: "auth-buttons" },
      React.createElement("button", { className: "buttonSecondary", onClick: handleLogOut }, "Log Out")
    ),
    React.createElement("h3", null, "What are you looking to flip today?"),
    React.createElement("div", { className: "stock-buttons" },
      ["Macbook", "iPhone", "AirPods", "Vitamix", "PS5", "KitchenAid Mixer"].map((label, i) =>
        React.createElement("button", {
          key: i,
          className: "stock-button",
          onClick: () => handleSelectPreference(label)
        }, label)
      )
    ),
    searchInputs.map((input, i) =>
      React.createElement("div", { key: i, style: { marginBottom: "10px" } },
        React.createElement("input", {
          type: "text",
          placeholder: "Enter search like: 'Macbook Pro used'",
          value: input,
          onChange: e => handleInputChange(i, e.target.value),
          style: { width: "100%", padding: "10px", fontSize: "16px" }
        }),
        searchInputs.length > 1 &&
        React.createElement("button", { onClick: () => removeSearchField(i) }, "Remove")
      )
    ),
    React.createElement("div", null,
      React.createElement("button", { className: "buttonSecondary", onClick: addSearchField }, "Add Another"),
      React.createElement("button", { className: "buttonPrimary", onClick: handleSearch, disabled: isLoading }, "Search")
    ),
    isLoading && React.createElement("div", { className: "loader" }),
    isLoading && React.createElement("div", {
      style: { marginTop: "10px", fontSize: "16px", color: "#555" }
    }, 
      "Listings searched: ",
      React.createElement("span", { style: { color: "#4CAF50", fontWeight: "bold" } }, listingsSearched)
    ),    
    React.createElement("div", { className: "result-box", style: { marginTop: "20px" } },
      React.createElement("h2", null, "Top Resale Opportunities"),
      results.length > 0 ? results.map((item, i) =>
        React.createElement("div", {
          key: i,
          style: {
            display: "flex",
            alignItems: "center",
            marginBottom: "20px",
            justifyContent: "space-between"
          }
        },
          // ⭐ Star button
          React.createElement("button", {
            onClick: () => toggleSaveItem(item),
            style: {
              fontSize: "24px",
              background: "none",
              border: "none",
              cursor: "pointer",
              color: savedItems.some(i => i.url === item.url) ? "gold" : "#ccc",
              marginRight: "10px"
            }
          }, "★"),
          React.createElement("a", {
            href: item.url,
            target: "_blank",
            rel: "noopener noreferrer",
            onClick: () => {
              fetch("https://flipfinder.onrender.com/log_click", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  url: item.url,
                  title: item.title,
                  username: username || "Anonymous"
                })
              }).catch(err => console.error("Click log failed:", err));
            },
            style: {
              display: "flex",
              alignItems: "center",
              textDecoration: "none",
              color: "inherit",
              gap: "12px",
              flexGrow: 1
            }
          },          
            item.thumbnail &&
            React.createElement("img", {
              src: item.thumbnail,
              alt: item.title,
              style: {
                width: "100px",
                height: "auto",
                objectFit: "cover",
                borderRadius: "10px",
                boxShadow: "0 0 4px rgba(0,0,0,0.15)"
              }
            }),
            React.createElement("div", { className: "details" },
              React.createElement("div", null, item.title),
              React.createElement("div", { className: "price" },
                `$${item.price.toFixed(2)}`,
                item.shipping !== undefined &&
                  ` (incl. $${item.shipping.toFixed(2)} shipping)`
              )
                          )
          ),
          React.createElement("div", {
            className: "profit",
            style: {
              color: item.profit_color === "red" ? "red" : "#2ecc71",
              fontSize: "36px",
              fontWeight: "bold",
              marginLeft: "10px"
            }
          }, `$${item.profit.toFixed(2)}`)
        )
      ) : React.createElement("p", null, "No results yet."),
      React.createElement("div", { className: "saved-box", style: { marginTop: "60px" } },
        React.createElement("h2", null, "⭐ Saved Listings"),
        savedItems.length > 0
          ? savedItems.map((item, i) =>
              React.createElement("div", {
                key: `saved-${i}`,
                style: {
                  display: "flex",
                  alignItems: "center",
                  marginBottom: "20px",
                  justifyContent: "space-between"
                }
              },
                React.createElement("a", {
                  href: item.url,
                  target: "_blank",
                  rel: "noopener noreferrer",
                  style: {
                    display: "flex",
                    alignItems: "center",
                    textDecoration: "none",
                    color: "inherit",
                    gap: "12px",
                    flexGrow: 1
                  }
                },
                  item.thumbnail &&
                  React.createElement("img", {
                    src: item.thumbnail,
                    alt: item.title,
                    style: {
                      width: "100px",
                      height: "auto",
                      objectFit: "cover",
                      borderRadius: "10px",
                      boxShadow: "0 0 4px rgba(0,0,0,0.15)"
                    }
                  }),
                  React.createElement("div", { className: "details" },
                    React.createElement("div", null, item.title),
                    React.createElement("div", { className: "price" },
                      `$${item.price.toFixed(2)}`,
                      item.shipping !== undefined &&
                        ` (incl. $${item.shipping.toFixed(2)} shipping)`
                    )
                                      )
                ),
                React.createElement("div", {
                  className: "profit",
                  style: {
                    color: item.profit >= 0 ? "#2ecc71" : "red",
                    fontSize: "24px",
                    fontWeight: "bold",
                    marginLeft: "10px"
                  }
                }, `$${item.profit.toFixed(2)}`),
                React.createElement("button", {
                  onClick: () => toggleSaveItem(item),
                  style: {
                    fontSize: "20px",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: "gold",
                    marginLeft: "10px"
                  }
                }, "★"),
                React.createElement("label", {
                  style: {
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    fontSize: "14px",
                    marginLeft: "10px"
                  }
                },
                  "Auto-search",
                  React.createElement("input", {
                    type: "checkbox",
                    checked: autoSearches.includes(item.title),
                    onChange: (e) => {
                      toggleAutoSearch(item.title, e.target.checked);
                      setAutoSearches(prev => {
                        if (e.target.checked) {
                          return [...prev, item.title];
                        } else {
                          return prev.filter(q => q !== item.title);
                        }
                      });
                    }
                  })
                )                
              )
            )
          : React.createElement("p", null, "You haven't saved any listings yet.")
      )
    )
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(React.createElement(App));
