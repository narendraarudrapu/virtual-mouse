import app from './firebase-init.js';
import { getAuth, GoogleAuthProvider, signInWithPopup } from 'firebase/auth';

const auth = getAuth(app);
const provider = new GoogleAuthProvider();

export async function signInWithGoogle() {
  try {
    const result = await signInWithPopup(auth, provider);
    // The signed-in user info.
    return result.user;
  } catch (error) {
    // Propagate error to caller for handling
    throw error;
  }
}

export { auth, provider };

<button id="google-signin">Sign in with Google</button>

<script type="module">
  import { signInWithGoogle } from '/static/js/firebase-auth.js';
  document.getElementById('google-signin').addEventListener('click', async () => {
    try {
      const user = await signInWithGoogle();
      console.log(user);
      window.location = '/dashboard';
    } catch (e) {
      console.error(e);
      alert('Sign-in failed');
    }
  });
</script>
