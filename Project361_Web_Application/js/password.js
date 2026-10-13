//eyeButton at the password on the login/sign-up page
//
function togglePassword(inputId) {
  // If you call it with ID, use that ID. If you call it without ID, use 'password' by default
  let id = inputId || 'password';
  const input = document.getElementById(id);
  
  if (!input) return; // safety

  if (input.type === 'password') {
    input.type = 'text';
  } else {
    input.type = 'password';
  }
}
