// Project361 Logout

import { signOut } from "https://www.gstatic.com/firebasejs/12.18.0/firebase-auth.js";
import { auth } from "./firebase-config.js";

const logoutButton = document.getElementById("logoutButton");

if (logoutButton) {
    logoutButton.addEventListener("click", async () => {
        logoutButton.disabled = true;
        logoutButton.textContent = "Logging out...";

        try {
            await signOut(auth);
            window.location.replace("login.html");
        } catch (error) {
            console.error("Logout error:", error);
            logoutButton.disabled = false;
            logoutButton.textContent = "Log out";
            alert("Unable to log out. Please try again.");
        }
    });
}
