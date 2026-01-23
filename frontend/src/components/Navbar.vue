<script>
export default {
  name: 'Navbar',
  props: {
    theme: {
      type: String,
      default: 'default', // Changed back to default
      validator: value => ['default', 'light', 'dark'].includes(value)
    },
    position: {
      type: String,
      default: 'sticky',
      validator: value => ['static', 'sticky', 'fixed'].includes(value)
    }
  },
  data() {
    return {
      isScrolled: false,
      isMenuOpen: false,
      isMobile: false,
      resizeTimer: null
    }
  },
  computed: {
    navbarClasses() {
      return [
        `navbar-${this.theme}`,
        `navbar-${this.position}`,
        { 'navbar-scrolled': this.isScrolled }
      ]
    }
  },
  mounted() {
    this.checkMobile()
    window.addEventListener('resize', this.handleResize)
    window.addEventListener('scroll', this.handleScroll)
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize)
    window.removeEventListener('scroll', this.handleScroll)
  },
  methods: {
    handleScroll() {
      this.isScrolled = window.scrollY > 20
    },
    handleResize() {
      clearTimeout(this.resizeTimer)
      this.resizeTimer = setTimeout(() => {
        this.checkMobile()
        if (!this.isMobile && this.isMenuOpen) {
          this.isMenuOpen = false
        }
      }, 200)
    },
    checkMobile() {
      this.isMobile = window.innerWidth <= 768
    },
    toggleMenu() {
      this.isMenuOpen = !this.isMenuOpen
    }
  }
}
</script>

<template>
  <header
    class="navbar"
    :class="navbarClasses"
    role="banner"
  >
    <div class="logo-container" aria-label="PPTAS Logo">
      <div class="logo-icon">
        <span class="icon-inner">🧬</span>
      </div>
      <div class="logo-text">
        <span class="brand-name">PPTAS</span>
        <span class="brand-tagline">AI Content Agent</span>
      </div>
    </div>

    <button
      class="mobile-menu-btn"
      @click="toggleMenu"
      aria-label="切换菜单"
      v-if="isMobile"
    >
      <span :class="{ 'open': isMenuOpen }"></span>
      <span :class="{ 'open': isMenuOpen }"></span>
      <span :class="{ 'open': isMenuOpen }"></span>
    </button>

    <div class="nav-actions" :class="{ 'active': isMenuOpen }">
      <slot></slot>
    </div>
  </header>
</template>

<style scoped>
.navbar {
  padding: 0.75rem 5%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  width: 100%;
  box-sizing: border-box;
  z-index: 1000;
  border-bottom: 1px solid transparent;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.logo-icon {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-size: 1.25rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.02em;
  line-height: 1;
}

.brand-tagline {
  font-size: 0.7rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

/* Themes */
.navbar-default {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #ffffff;
}

.navbar-default .brand-name { color: #ffffff; }
.navbar-default .brand-tagline { color: rgba(255, 255, 255, 0.85); }
.navbar-default .logo-icon { 
  background: rgba(255, 255, 255, 0.2); 
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.navbar-default .mobile-menu-btn span { background: #ffffff; }

.navbar-light {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  color: #0f172a;
  border-bottom: 1px solid #f1f5f9;
}

.navbar-dark {
  background: #1a202c;
  color: #ffffff;
}

.navbar-dark .brand-name { color: #ffffff; }

.navbar-sticky {
  position: sticky;
  top: 0;
}

.navbar-scrolled {
  padding: 0.5rem 5%;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
  border-bottom: 1px solid #f1f5f9;
}

.mobile-menu-btn {
  display: none;
  flex-direction: column;
  justify-content: space-around;
  width: 24px;
  height: 24px;
  background: transparent;
  border: none;
  cursor: pointer;
  z-index: 1001;
  padding: 0;
}

.mobile-menu-btn span {
  width: 24px;
  height: 2px;
  background: #0f172a;
  border-radius: 10px;
  transition: all 0.3s ease;
}

.mobile-menu-btn span.open:first-child { transform: translateY(8px) rotate(45deg); }
.mobile-menu-btn span.open:nth-child(2) { opacity: 0; }
.mobile-menu-btn span.open:nth-child(3) { transform: translateY(-8px) rotate(-45deg); }

@media (max-width: 768px) {
  .mobile-menu-btn { display: flex; }
  .nav-actions {
    position: fixed;
    top: 0;
    right: 0;
    height: 100vh;
    width: 280px;
    background: #ffffff;
    flex-direction: column;
    padding: 5rem 2rem;
    box-shadow: -10px 0 30px rgba(0,0,0,0.1);
    transform: translateX(100%);
    transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .nav-actions.active { transform: translateX(0); }
}
</style>
