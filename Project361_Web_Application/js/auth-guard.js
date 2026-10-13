// Project361 Dashboard Authentication Guard

import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/12.18.0/firebase-auth.js";
import { auth } from "./firebase-config.js";

onAuthStateChanged(auth, (user) => {
    if (user) {
        // Authentication has been confirmed.
        document.body.style.visibility = "visible";
        document.body.classList.remove("auth-checking");
    } else {
        // No authenticated user: leave the protected page immediately.
        window.location.replace("login.html");
    }
});
