const imageInput = document.getElementById('image_file');
const preview = document.getElementById('image_preview');
const themeToggle = document.getElementById('theme_toggle');

function setTheme(theme) {
  document.body.setAttribute('data-theme', theme);

  if (themeToggle) {
    if (theme === 'dark') {
      themeToggle.textContent = '☀️ Light Mode';
      themeToggle.setAttribute('aria-label', 'Switch to light mode');
    } else {
      themeToggle.textContent = '🌙 Dark Mode';
      themeToggle.setAttribute('aria-label', 'Switch to dark mode');
    }
  }
}

function initTheme() {
  const saved = localStorage.getItem('theme_preference');
  if (saved === 'dark' || saved === 'light') {
    setTheme(saved);
    return;
  }

  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  setTheme(prefersDark ? 'dark' : 'light');
}

if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const current = document.body.getAttribute('data-theme') || 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    setTheme(next);
    localStorage.setItem('theme_preference', next);
  });
}

initTheme();

if (imageInput && preview) {
  imageInput.addEventListener('change', () => {
    const file = imageInput.files && imageInput.files[0];
    if (!file) {
      preview.style.display = 'none';
      preview.removeAttribute('src');
      return;
    }

    const url = URL.createObjectURL(file);
    preview.src = url;
    preview.style.display = 'block';

    preview.onload = () => {
      URL.revokeObjectURL(url);
    };
  });
}
