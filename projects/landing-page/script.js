/* ===================================================================
   Vibe Coding — Landing Page Dynamic Interactions & Animations
   =================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Lucide Icons
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }

  // --- Theme Toggle (Dark / Light) ---
  const htmlElement = document.documentElement;
  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  const sunIcon = document.querySelector('.sun-icon');
  const moonIcon = document.querySelector('.moon-icon');

  // Check saved theme or system preference
  const savedTheme = localStorage.getItem('theme');
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const initialTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');

  setTheme(initialTheme);

  themeToggleBtn.addEventListener('click', () => {
    const currentTheme = htmlElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
  });

  function setTheme(theme) {
    htmlElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);

    if (theme === 'dark') {
      if (sunIcon) sunIcon.style.display = 'block';
      if (moonIcon) moonIcon.style.display = 'none';
    } else {
      if (sunIcon) sunIcon.style.display = 'none';
      if (moonIcon) moonIcon.style.display = 'block';
    }
  }

  // --- Navbar Scroll Effect ---
  const navbar = document.getElementById('navbar');
  
  const handleScroll = () => {
    if (window.scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  };

  window.addEventListener('scroll', handleScroll);
  handleScroll(); // Run once in case page loaded scrolled down

  // --- Scroll Animation Trigger (Intersection Observer) ---
  const animatedElements = document.querySelectorAll('.animate-on-scroll');

  const observerOptions = {
    root: null,
    rootMargin: '0px',
    threshold: 0.1
  };

  const scrollObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target); // Animates only once
      }
    });
  }, observerOptions);

  animatedElements.forEach(element => {
    scrollObserver.observe(element);
  });

  // --- Copy to Clipboard Command ---
  const copyBtn = document.getElementById('copy-cmd-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      const commandText = "powershell -ExecutionPolicy Bypass -File .\\setup.ps1";
      navigator.clipboard.writeText(commandText)
        .then(() => {
          // Temporarily swap copy icon for checkmark
          const icon = copyBtn.querySelector('i') || copyBtn;
          if (icon && typeof lucide !== 'undefined') {
            icon.setAttribute('data-lucide', 'check');
            lucide.createIcons();
            
            setTimeout(() => {
              icon.setAttribute('data-lucide', 'copy');
              lucide.createIcons();
            }, 2000);
          }
        })
        .catch(err => {
          console.error('Command copy failed: ', err);
        });
    });
  }

  // --- Mobile Menu Toggle ---
  const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
  const navLinks = document.querySelector('.nav-links');

  if (mobileMenuToggle && navLinks) {
    mobileMenuToggle.addEventListener('click', () => {
      const isExpanded = mobileMenuToggle.getAttribute('aria-expanded') === 'true';
      mobileMenuToggle.setAttribute('aria-expanded', !isExpanded);
      navLinks.classList.toggle('active');
      mobileMenuToggle.classList.toggle('active');
    });

    // Close menu when link is clicked
    document.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('active');
        mobileMenuToggle.classList.remove('active');
        mobileMenuToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }
});
