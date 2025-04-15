// Full Flip Finder app with login and post-login search functionality
const { useState, useEffect } = React;

function App() {
  const [autoSearches, setAutoSearches] = useState([]);
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
  const [classicLimitReached, setClassicLimitReached] = useState(false);
  const [showSignup, setShowSignup] = useState(false);
  const ZIP_API_KEY = "9d2e0c1df7754fac9df73a6a7addd9ec";
  const [showAccountPopup, setShowAccountPopup] = useState(false);
  const [showEmailSchedule, setShowEmailSchedule] = useState(false);
  const [emailDays, setEmailDays] = useState([]);
  const [showUsernameModal, setShowUsernameModal] = useState(false);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = React.useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [email, setEmail] = useState("");
  const [userCity, setUserCity] = useState("");
  const [userState, setUserState] = useState("");
  const [kslResults, setKslResults] = useState([]);
  const [ebayResults, setEbayResults] = useState([]);


  
  



  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    const storedPrefs = localStorage.getItem("userPreferences");
    const storedZip = localStorage.getItem("zip");
    const storedCity = localStorage.getItem("city");
    const storedState = localStorage.getItem("state");
  
    if (storedUser) {
      setUsername(storedUser);
      setIsAuthenticated(true);
      setUserPreferences(JSON.parse(storedPrefs || "[]"));
  
      // 🔁 Load saved auto-searches
      fetch(`https://flipfinder.onrender.com/user_auto_searches/${storedUser}`)
        .then(res => res.json())
        .then(data => {
          const enabled = data
            .filter(s => s.auto_search_enabled)
            .map(s => s.query_text);
          setAutoSearches(enabled);
          setSearchInputs(enabled.length > 0 ? enabled : [""]);
        })
        .catch(err => console.error("Failed to load auto-searches:", err));
    }
  
    if (storedZip) {
      setUserZip(storedZip);
    }
    if (storedCity) {
      setUserCity(storedCity);
    }
    if (storedState) {
      setUserState(storedState);
    }
  
    // ✅ Fallback if ZIP wasn’t already stored
    if (!storedZip || !storedCity || !storedState) {
      fetchZipFromLocation()
        .then(({ zip, city, state }) => {
          if (zip) {
            setUserZip(zip);
            localStorage.setItem("zip", zip);
          }
          if (city) {
            setUserCity(city);
            localStorage.setItem("city", city);
          }
          if (state) {
            setUserState(state);
            localStorage.setItem("state", state);
          }
          console.log("🌎 Location loaded:", { zip, city, state });
        })
        .catch(err => console.warn("Could not get ZIP/city/state from geolocation:", err));
    }
  }, []);
  
 
  useEffect(() => {
    if (!username) return;
  
    fetch(`https://flipfinder.onrender.com/saved_items/${username}`)
      .then(res => res.json())
      .then(data => {
        setSavedItems(data || []);
      })
      .catch(err => console.error("Failed to load saved items:", err));
  }, [username]);
  
  async function fetchUserInfo() {
    if (!username) return;
  
    try {
      const res = await fetch(`https://flipfinder.onrender.com/get_email/${username}`);
      if (!res.ok) {
        console.error("❌ Failed to fetch user email:", res.statusText);
        return;
      }
      const data = await res.json();
      //console.log("📬 Pulled email from server:", data.email);
      setUserEmail(data.email);
    } catch (err) {
      console.error("❌ Error fetching user email:", err);
    }
  }
  
  fetchUserInfo();
  

  // ✅ Handle opening the email schedule modal
  async function handleOpenEmailSchedule() {
    console.log("🟢 Email schedule button clicked!");
  
    try {
      const res = await fetch(`https://flipfinder.onrender.com/get_email_days/${username}`);
      const data = await res.json();
      if (res.ok) {
        setEmailDays(data.days || []);
        setShowEmailSchedule(true);
      } else {
        setEmailDays([]);
        setShowEmailSchedule(true);
      }
    } catch (err) {
      console.error("Failed to load email days:", err);
      setEmailDays([]);
      setShowEmailSchedule(true);
    }
  
    setShowAccountPopup(false);
  }
  
  // ✅ Handle opening the username modal
  async function handleOpenUsernameModal() {
    console.log("🟢 Change Username button clicked!");
    setShowAccountPopup(false);
    setShowUsernameModal(true);
    
  }
    
  async function handleOpenPasswordModal() {
    setShowAccountPopup(false);
   console.log(userEmail)
   console.log("this is before")
    // Check if the email is already loaded
    if (userEmail) {
      console.log("🔐 Opening password reset modal with existing email...");
      setShowPasswordModal(true); // Modal opens with email already set
    } else {
      console.log("📬 Fetching email before opening the password modal...");
      try {
        const res = await fetch(`https://flipfinder.onrender.com/get_email/${username}`);
        const data = await res.json();
        if (res.ok) {
          //console.log("📬 Pulled email from server:", data.email);
          setUserEmail(data.email);  // Set the fetched email
          setTimeout(() => {
            setShowPasswordModal(true); // Ensure modal opens after email is set
          }, 100); // Delay slightly to allow state update to take place
        } else {
          console.error("❌ Failed to load email:", data.detail);
        }
      } catch (err) {
        console.error("❌ Error fetching email:", err);
      }
    }
  }
  
  

  
  
  

  async function handleOpenEmailModal() {
    console.log("📧 Opening change email modal...");
    setShowAccountPopup(false);
  
    try {
      const res = await fetch(`https://flipfinder.onrender.com/get_email/${username}`);
      const data = await res.json();
      if (res.ok) {
        setEmail(data.email);
        setShowEmailModal(true);
      } else {
        console.error("Failed to load email:", data.detail);
      }
    } catch (err) {
      console.error("Error fetching email:", err);
    }
  }
  
  
  window.handleOpenEmailModal = handleOpenEmailModal;  
  window.handleOpenEmailSchedule = handleOpenEmailSchedule;
  window.handleOpenUsernameModal = handleOpenUsernameModal; // ✅ THIS is what’s missing
  window.setShowUsernameModal = setShowUsernameModal;
  window.ChangeUsernameModal = ChangeUsernameModal;
  window.handleOpenPasswordModal = handleOpenPasswordModal;
  window.handleOpenDeleteModal = () => {
    console.log("🗑️ Delete Account button clicked");
    setShowAccountPopup(false);
    setShowDeleteModal(true);
  };
  


  
  
  
  async function toggleAutoSearch(queryText, enable) {
    const endpoint = enable ? "enable_auto_search" : "disable_auto_search";
    const url = `https://flipfinder.onrender.com/${endpoint}`;
  
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          query_text: queryText
        })
      });
  
      const data = await res.json();
  
      if (!res.ok) {
        console.error(`❌ ${endpoint} failed:`, data.detail || data);
        //alert(`Failed to ${enable ? "enable" : "disable"} auto-search: ${data.detail}`);
      } else {
        console.log(`✅ Auto-search ${enable ? "enabled" : "disabled"} for "${queryText}"`);
      }
    } catch (err) {
      console.error("🔥 Network error toggling auto-search:", err);
    }
  }
  
  
  
  

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
        window.location.href = "/confirmation.html";
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
            `https://api.opencagedata.com/geocode/v1/json?q=${latitude}+${longitude}&key=${ZIP_API_KEY}`
          );
  
          const data = await response.json();
          const components = data?.results?.[0]?.components;
  
          const zip = components?.postcode || null;
          const city = components?.city || components?.town || components?.village || null;
          const state = components?.state_code || null;
  
          resolve({ zip, city, state });
        } catch (err) {
          console.error("Failed to fetch ZIP/city/state from OpenCage:", err);
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
        window.location.reload();
      }else {
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
  
    const endpoint = alreadySaved ? "unsave_item" : "save_item";
  
    try {
      await fetch(`https://flipfinder.onrender.com/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, item })
      });
    } catch (err) {
      console.error(`Failed to ${alreadySaved ? "unsave" : "save"} item:`, err);
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
      setClassicLimitReached(true); // 👈 show message
      return;
    }
    setSearchInputs([...searchInputs, ""]);
    setClassicLimitReached(false); // 👈 hide message if they add successfully
  }
  

  function removeSearchField(index) {
    const newInputs = [...searchInputs];
    const removedSearch = newInputs[index];
    newInputs.splice(index, 1);
    setSearchInputs(newInputs);
  
    // Disable auto-search if the removed search was active
    if (autoSearches.includes(removedSearch)) {
      toggleAutoSearch(removedSearch, false);
      setAutoSearches(prev => prev.filter(q => q !== removedSearch));
    }
  
    // (Optional) also remove from backend if needed
    fetch("https://flipfinder.onrender.com/remove_search_and_disable_auto", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        username,  // ✅ use actual username
        query_text: removedSearch  // ✅ this is the query string
      })
    })
      .then((res) => res.json())
      .then((data) => {
        console.log("✅ Backend removed saved search:", data);
      })
      .catch((err) => {
        console.error("❌ Error removing saved search:", err);
      });
  }
  
  

  async function handleSearch() {
    setIsLoading(true);
    setKslResults([]);      // ✅ You must declare these state variables in your component
    setEbayResults([]);
    setParsedQueries([]);
    setListingsSearched(0);
  
    const evtSource = new EventSource("https://flipfinder.onrender.com/events");
  
    evtSource.onmessage = function (event) {
      try {
        const msg = JSON.parse(event.data);
  
        if (msg.type === "increment") {
          setListingsSearched(prev => prev + 1);
        } else if (msg.type === "new_result") {
          const item = msg.data;
  
          if (item._source === "ksl") {
            setKslResults(prev => {
              const updated = [...prev, item];
              return updated
                .filter((item, index, self) =>
                  index === self.findIndex(i =>
                    i.url === item.url ||
                    (i.title === item.title && i.price === item.price)
                  )
                )
                .sort((a, b) => b.profit - a.profit)
                .slice(0, 5);
            });
          } else if (item._source === "ebay") {
            setEbayResults(prev => {
              const updated = [...prev, item];
              return updated
                .filter((item, index, self) =>
                  index === self.findIndex(i =>
                    i.url === item.url ||
                    (i.title === item.title && i.price === item.price)
                  )
                )
                .sort((a, b) => b.profit - a.profit)
                .slice(0, 5);
            });
          }
        }
      } catch (err) {
        if (event.data === "increment") {
          setListingsSearched(prev => prev + 1);
        } else {
          console.warn("Unhandled event stream data:", event.data);
        }
      }
    };
  
    console.log("📍 Location state:", { userZip, userCity, userState });
    if (!userCity || !userState) {
      alert("📍 Local KSL search requires location access. Please enable location services.");
      setIsLoading(false);
      evtSource.close();
      return;
    }
  
    try {
      const userQuery = searchInputs[0];
  
      const aiRes = await fetch("https://flipfinder.onrender.com/ai_search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          search: userQuery,
          postalCode: userZip || "10001"
        })
      });
  
      if (!aiRes.ok) throw new Error("AI search failed");
  
      const aiData = await aiRes.json();
      console.log("🧠 Parsed AI response:", aiData.parsed);
  
      const refinedQuery = aiData.parsed?.query || userQuery;
      const alt1 = aiData.parsed?.alt1 || null;
      const alt2 = aiData.parsed?.alt2 || null;
  
      // ✅ Start KSL immediately for user query
      console.log("🚀 [EARLY] KSL fetch sending for:", refinedQuery);
      const kslTask = fetch("https://flipfinder.onrender.com/ksl_deals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          search: refinedQuery,
          city: userCity,
          state: userState
        })
      }).then(res => res.json())
        .then(() => console.log("✅ [EARLY] KSL done for:", refinedQuery))
        .catch(err => console.error("❌ [EARLY] KSL fetch crashed:", err));
  
      const allQueries = [
        { source: "user", query: refinedQuery },
        ...(alt1 ? [{ source: "alt1", query: alt1 }] : []),
        ...(alt2 ? [{ source: "alt2", query: alt2 }] : [])
      ];
  
      const queryTasks = allQueries.map(async ({ source, query }) => {
        try {
          const ebayRes = await fetch("https://flipfinder.onrender.com/ai_search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              search: query,
              postalCode: userZip || "10001"
            })
          });
  
          if (!ebayRes.ok) throw new Error("eBay request failed");
  
          const ebayData = await ebayRes.json();
  
          const ebayResults = ebayData.results.map(r => ({
            ...r,
            _parsed: ebayData.parsed,
            _source: "ebay"
          }));
  
          ebayResults.forEach(item => {
            setEbayResults(prev => {
              const updated = [...prev, item];
              return updated
                .filter((item, index, self) =>
                  index === self.findIndex(i =>
                    i.url === item.url ||
                    (i.title === item.title && i.price === item.price)
                  )
                )
                .sort((a, b) => b.profit - a.profit)
                .slice(0, 5);
            });
          });
  
          setParsedQueries(prev => [...prev, ebayData.parsed]);
  
          console.log(`✅ eBay finished for ${source} query:`, query);
        } catch (err) {
          console.error(`❌ Error with ${source} query "${query}":`, err);
        }
      });
  
      await Promise.all([
        ...queryTasks,
        kslTask
      ]);
    } catch (error) {
      alert("Error performing the search.");
      console.error("Search error:", error);
    } finally {
      evtSource.close();
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
        alt: "Resale Radar Logo",
        style: {
          width: "450px",
          marginBottom: "20px",
          marginTop: "-275px",
          marginBottom: "20px",
        }
      }),
      React.createElement("div", { className: "subtitle" },
        "Discover deals, track profits, and resell goods"
      ),      
      React.createElement("div", { className: "subtitle" },
        "with your personal resale assistant!"
      ),      
      React.createElement("form", { onSubmit: handleLoginSubmit, style: { maxWidth: "300px", width: "100%" } },
        ["email", "password"].map((field) =>
          React.createElement("div", { key: field, style: { marginBottom: "10px", marginTop: "20px" } },
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
      React.createElement("button", {
        type: "button",
        className: "signup-toggle",
        onClick: () => {
          const email = prompt("Enter your email to reset password:");
          if (!email) return;
      
          fetch("https://flipfinder.onrender.com/request_password_reset", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: userEmail })  // ✅ Must match pydantic model in backend
          })
          
            .then(res => res.json())
            .then(data => alert(data.message || "If your email exists, you will receive a reset link."))
            .catch(err => alert("Something went wrong. Please try again."));
        }
      }, "Forgot your password?"),
      
      React.createElement("div", { style: { marginTop: "20px" } },
        React.createElement("h4", null, "Don't have an account?"),
        !showSignup && React.createElement("button", {
          type: "button",
          className: "signup-toggle",
          onClick: () => setShowSignup(true)
        }, "Sign Up"),
        React.createElement("div", {
          style: { display: "flex", justifyContent: "center", width: "100%" }
        },
          React.createElement("form", {
            onSubmit: handleSignupSubmit,
            className: `signup-slide ${showSignup ? "show" : ""}`,
            style: { maxWidth: "350px", width: "100%" }
          },
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
            ).concat([
              React.createElement("button", {
                type: "submit",
                className: "buttonSecondary",
                style: { width: "100%", padding: "10px" }
              }, "Submit"),
              signupMessage && React.createElement("p", null, signupMessage)
            ])
          )
        )      
      )      
    );
  }

  return React.createElement("div", { style: { maxWidth: "800px", margin: "auto", padding: "20px" } },
    React.createElement("div", { className: "logo-wrapper" },
      React.createElement("img", {
        src: "assets/flip finder logo.png",
        alt: "Resale Logo",
        height: "250"
      })
    ),
    React.createElement("div", {
      id: "auth-buttons",
      style: {
        position: "absolute",
        top: "20px",
        right: "20px",
        display: "flex",
        alignItems: "center",
        gap: "10px",
        zIndex: 100
      }
    },    
    React.createElement("img", {
      src: "assets/logoicon.png",
      alt: "Account",
      style: {
        width: "34px",
        height: "34px",
        cursor: "pointer",
        borderRadius: "50%",
        boxShadow: "0 0 6px rgba(0,0,0,0.1)"
      },
      onClick: () => setShowAccountPopup(prev => !prev)
    }),
    React.createElement("button", { className: "buttonSecondary", onClick: handleLogOut }, "Log Out"),

showAccountPopup && React.createElement(window.AccountPopup, { onClose: () => setShowAccountPopup(false) }),


showEmailSchedule && React.createElement(window.EmailScheduleModal, {
  username,
  selectedDays: emailDays,
  onClose: () => setShowEmailSchedule(false),
  onSave: (days) => {
    setEmailDays(days);
    setShowEmailSchedule(false);

    if (days.length === 0) {
      autoSearches.forEach(q => toggleAutoSearch(q, false));
      setAutoSearches([]);
    }
  }
}),
// Log the email before rendering the modal to ensure it's correct

// Ensure the modal is rendered with the correct `email`
showDeleteModal && React.createElement(window.DeleteAccountModal, {
  userEmail: userEmail,  // Pass email as userEmail to the modal
  onClose: () => setShowDeleteModal(false),  // Close the modal when clicked
  onConfirm: async () => {
    console.log("Email inside onConfirm:", userEmail);  // Log email inside the onConfirm function

    try {
      console.log("trying to delete", userEmail)
      const res = await fetch("https://flipfinder.onrender.com/delete_account", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({userEmail})  // Pass the email for account deletion
      });

      if (res.ok) {
        localStorage.removeItem("user");
        //alert("✅ Account deleted.");
        window.location.reload();  // Reload the page after successful deletion
      } else {
        alert("❌ Failed to delete account.");
      }
    } catch (err) {
      console.error("Error deleting account:", err);
      alert("❌ Error deleting account.");
    }
  }
}),

showEmailModal && React.createElement(window.ChangeEmailModal, {
  currentEmail: email,
  onClose: () => setShowEmailModal(false),
  onSave: (newEmail) => {
    setEmail(newEmail);
    localStorage.setItem("email", newEmail);
    setShowEmailModal(false);
  }
}),

showPasswordModal && React.createElement(window.ChangePasswordModal, {
  userEmail: userEmail,
  onClose: () => setShowPasswordModal(false)
}),

showUsernameModal && React.createElement(window.ChangeUsernameModal, {

  currentUsername: username,
  onClose: () => setShowUsernameModal(false),
  onSave: (newName) => {
    setUsername(newName);
    localStorage.setItem("user", newName);
    setShowUsernameModal(false);
  }
})

   
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
      React.createElement("div", {
        key: i,
        style: {
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginBottom: "14px"
        }
      },
        // Search input box
        React.createElement("input", {
          type: "text",
          placeholder: "Enter search like: 'Macbook Pro used'",
          value: input,
          onChange: async (e) => {
            const oldQuery = searchInputs[i];
            const newQuery = e.target.value;
        
            if (autoSearches.includes(oldQuery)) {
              setAutoSearches(prev => prev.filter(q => q !== oldQuery));
              await toggleAutoSearch(oldQuery, false);
            }
        
            const newInputs = [...searchInputs];
            newInputs[i] = newQuery;
            setSearchInputs(newInputs);
          },
          style: {
            flex: 1,
            padding: "10px",
            fontSize: "16px"
          }
        }),        
    
        React.createElement("div", {
          style: {
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            marginRight: "8px"
          }
        },
          React.createElement("span", {
            style: {
              fontSize: "12px",
              color: "#555",
              marginBottom: "4px"
            }
          }, "AI Search Assistant"),
          React.createElement("label", {
            className: "switch",
            title: "Enable Auto-search"
          },
            React.createElement("input", {
              type: "checkbox",
              checked: autoSearches.includes(input),
              onChange: async (e) => {
                const isChecked = e.target.checked;
              
                // HARD LIMIT: Don't add more than 3
                if (isChecked && autoSearches.length > 3) {
                  return; // silently ignore
                }
              
                await toggleAutoSearch(input, isChecked);
              
                setAutoSearches(prev => {
                  if (isChecked) {
                    return [...prev, input];
                  } else {
                    return prev.filter(q => q !== input);
                  }
                });
              }
                         
            }),
            React.createElement("span", { className: "slider" })
          )          
        ),
        classicLimitReached &&
        React.createElement("p", {
          style: {
            color: "red",
            fontSize: "14px",
            marginTop: "6px",
            marginBottom: "10px",
            textAlign: "center"
          }
        }, "You’ve reached the maximum of 3 searches."),
    
        // Optional "Remove" button if there's more than 1 field
        searchInputs.length > 1 &&
        React.createElement("button", {
          onClick: () => removeSearchField(i)
        }, "Remove")
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
      "Listings Searched: ",
      React.createElement("span", { style: { color: "#4CAF50", fontWeight: "bold" } }, listingsSearched)
    ),    
    kslResults.length > 0 &&
    React.createElement("div", {
      className: "result-box",
      style: { marginBottom: "30px", background: "#fdfdfd" }
    },
      React.createElement("h2", null, "Local KSL Listings"),
      kslResults.map((item, i) =>
        React.createElement("div", {
          key: `ksl-${item.url}`,
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
              item.location &&
              React.createElement("div", {
                style: { fontSize: "14px", color: "#666", marginTop: "4px" }
              }, `Location: ${item.location}`),
              React.createElement("div", { className: "price" }, `$${item.price.toFixed(2)}`)
            )
          ),
          React.createElement("div", {
            style: {
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-end",
              marginLeft: "10px"
            }
          }, [
            React.createElement("span", {
              key: "label",
              style: {
                fontSize: "12px",
                fontWeight: "bold",
                color: "#888",
                marginBottom: "4px"
              }
            }, "Potential Profit"),
            React.createElement("span", {
              key: "value",
              className: "profit",
              style: {
                color: item.profit >= 0 ? "#2ecc71" : "red",
                fontSize: "24px",
                fontWeight: "bold"
              }
            }, `$${item.profit.toFixed(2)}`)
          ])
        )
      )      
),
      ebayResults.length > 0 &&
      React.createElement("div", { className: "result-box", style: { marginTop: "20px", background: "#fdfdfd" } },
        React.createElement("h2", null, "Top Ebay Listings"),
        ebayResults.map((item, i) =>
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
            style: {
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-end",
              marginLeft: "10px"
            }
          }, [
            React.createElement("span", {
              key: "label",
              style: {
                fontSize: "12px",
                fontWeight: "bold",
                color: "#888",
                marginBottom: "4px"
              }
            }, "Potential Profit"),
            React.createElement("span", {
              key: "value",
              className: "profit",
              style: {
                color: item.profit >= 0 ? "#2ecc71" : "red",
                fontSize: "24px",
                fontWeight: "bold"
              }
            }, `$${item.profit.toFixed(2)}`)
          ]),          
        )
      ), React.createElement("p", null, "Local results can take up to 2 min to load."),
      
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
                  style: {
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "flex-end",
                    marginLeft: "10px"
                  }
                }, [
                  React.createElement("span", {
                    key: "label",
                    style: {
                      fontSize: "12px",
                      fontWeight: "bold",
                      color: "#888",
                      marginBottom: "4px"
                    }
                  }, "Potential Profit"),
                  React.createElement("span", {
                    key: "value",
                    className: "profit",
                    style: {
                      color: item.profit >= 0 ? "#2ecc71" : "red",
                      fontSize: "24px",
                      fontWeight: "bold"
                    }
                  }, `$${item.profit.toFixed(2)}`)
                ]),                
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
              )
            )
          : React.createElement("p", null, "You haven't saved any listings yet.")
      )
    )
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(React.createElement(App));
