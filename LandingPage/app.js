/**
 * Xeon - Scrcpy Controller GUI Landing Page Logic
 * Handles config loading, dynamic version injection, doc navigation, lightboxes, and smooth interactions.
 */

// Fallback configuration in case local file:// origin restricts fetch('config.json')
const DEFAULT_CONFIG = {
  appName: "Xeon - Scrcpy Controller GUI",
  latestVersion: "v1.0.0",
  latestDownloadUrl: "https://github.com/AlfandoXeon/ScrcpyControllerGUI/releases/download/ScrcpyController/XeonScrcpyController_Setup_v1.0.0.exe",
  latestReleaseDate: "September 6, 2026",
  latestFileSize: "56.4 MB",
  supportedOS: "Windows 10 / Windows 11 (64-bit)",
  githubRepo: "https://github.com/AlfandoXeon/ScrcpyControllerGUI",
  versions: [
    {
      version: "v1.0.0",
      releaseDate: "September 6, 2026",
      isLatest: true,
      tag: "v1.0.0",
      title: "Initial Official Production Release",
      downloadUrl: "https://github.com/AlfandoXeon/ScrcpyControllerGUI/releases/download/ScrcpyController/XeonScrcpyController_Setup_v1.0.0.exe",
      installerFileName: "XeonScrcpyController_Setup_v1.0.0.exe",
      fileSize: "56.4 MB",
      signature: "Authenticode Signed (CN=AlfandoXeon, DigiCert Timestamp)",
      description: "Initial stable production release featuring high-performance screen mirroring, low-latency audio capture, dedicated camera mode, OTG keyboard/mouse hardware simulation, device power management, embedded interactive ADB shell terminal, live color-coded application diagnostics, preset manager, and full Inno Setup 64-bit signed installer.",
      highlights: [
        "Complete GUI with 9 categorized control panels (Device, Display, Audio, Window, Advanced, Camera, Tools, OTG, Developer)",
        "Zero CMD pop-up windows via Windows API CREATE_NO_WINDOW and SW_HIDE execution flags",
        "Embedded interactive ADB Shell Terminal with security warning gates and quick inspection chips",
        "Direct lossless screenshot capture straight to host PC without temporary storage writes",
        "Reboot Power Tools (System, Recovery, Fastboot) with built-in safety confirmation modals",
        "Portable bundled runtime: Scrcpy v4.1, ADB Platform Tools, and SDL3 Direct3D renderer"
      ]
    }
  ]
};

let appConfig = DEFAULT_CONFIG;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize AOS
  if (typeof AOS !== 'undefined') {
    AOS.init({
      duration: 750,
      once: true,
      offset: 60,
      easing: 'ease-out-cubic'
    });
  }

  // Load configuration
  await loadConfiguration();

  // Populate dynamic UI
  applyConfigurationToUI();
  renderVersionsList();

  // Setup UI components
  setupMobileMenu();
  setupDocNavigation();
  setupLightbox();
  setupCodeCopyButtons();
  setupFAQAccordion();
});

/**
 * Fetch config.json or fall back safely
 */
async function loadConfiguration() {
  try {
    const response = await fetch('config.json');
    if (response.ok) {
      const data = await response.json();
      appConfig = { ...DEFAULT_CONFIG, ...data };
    }
  } catch (error) {
    console.warn("Using default embedded configuration (local origin mode):", error);
    appConfig = DEFAULT_CONFIG;
  }
}

/**
 * Update elements bound to config values
 */
function applyConfigurationToUI() {
  // Version badge
  document.querySelectorAll('.app-latest-version').forEach(el => {
    el.textContent = appConfig.latestVersion;
  });

  // Release date
  document.querySelectorAll('.app-latest-date').forEach(el => {
    el.textContent = appConfig.latestReleaseDate;
  });

  // File size
  document.querySelectorAll('.app-latest-size').forEach(el => {
    el.textContent = appConfig.latestFileSize;
  });

  // Download links
  document.querySelectorAll('.app-download-link').forEach(el => {
    el.setAttribute('href', appConfig.latestDownloadUrl);
  });

  // GitHub Repo link
  document.querySelectorAll('.app-github-link').forEach(el => {
    el.setAttribute('href', appConfig.githubRepo);
  });
}

/**
 * Render versions list in the Releases section
 */
function renderVersionsList() {
  const container = document.getElementById('versions-container');
  if (!container || !appConfig.versions) return;

  container.innerHTML = '';

  appConfig.versions.forEach(ver => {
    const card = document.createElement('div');
    card.className = 'card-elegant rounded-xl p-5 sm:p-7';

    const highlightsHtml = ver.highlights.map(item => `
      <li class="flex items-start text-xs text-slate-300">
        <svg class="w-3.5 h-3.5 text-blue-400 mr-2 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
        </svg>
        <span>${item}</span>
      </li>
    `).join('');

    card.innerHTML = `
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800">
        <div>
          <div class="flex items-center gap-2.5 mb-1.5">
            <span class="text-xl font-bold text-white tracking-tight">${ver.version}</span>
            ${ver.isLatest ? `
              <span class="px-2 py-0.5 rounded text-[11px] font-medium bg-blue-950/70 text-blue-300 border border-blue-800/60">
                Latest Release
              </span>
            ` : ''}
          </div>
          <p class="text-slate-400 text-xs">${ver.title} — Released on <span class="text-slate-200">${ver.releaseDate}</span></p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <a href="${ver.downloadUrl}" class="inline-flex items-center justify-center px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs transition-colors">
            <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
            </svg>
            Download Installer (${ver.fileSize})
          </a>
        </div>
      </div>

      <div class="mt-5">
        <p class="text-slate-300 text-xs leading-relaxed mb-5">${ver.description}</p>
        <h4 class="text-[11px] uppercase tracking-wider font-semibold text-slate-400 mb-3 font-mono">Release Highlights</h4>
        <ul class="grid grid-cols-1 md:grid-cols-2 gap-2.5 mb-5">
          ${highlightsHtml}
        </ul>

        <div class="p-3 rounded-lg bg-[#0d131f] border border-slate-800 text-[11px] text-slate-400 flex flex-wrap items-center justify-between gap-2 font-mono">
          <span>Security: <strong class="text-slate-300">${ver.signature}</strong></span>
          <span class="text-slate-400">${ver.installerFileName}</span>
        </div>
      </div>
    `;

    container.appendChild(card);
  });
}

/**
 * Mobile navigation menu toggling
 */
function setupMobileMenu() {
  const btn = document.getElementById('mobile-menu-btn');
  const menu = document.getElementById('mobile-menu');
  if (!btn || !menu) return;

  btn.addEventListener('click', () => {
    menu.classList.toggle('hidden');
  });

  menu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      menu.classList.add('hidden');
    });
  });
}

/**
 * Documentation Tabbed Navigation
 */
function setupDocNavigation() {
  const navButtons = document.querySelectorAll('.doc-nav-btn');
  const docPanels = document.querySelectorAll('.doc-panel');

  if (!navButtons.length || !docPanels.length) return;

  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');

      // Update active nav button styles
      navButtons.forEach(b => {
        b.classList.remove('bg-blue-600/10', 'text-blue-400', 'border-blue-600/30');
        b.classList.add('text-slate-400', 'border-transparent');
      });
      btn.classList.add('bg-blue-600/10', 'text-blue-400', 'border-blue-600/30');
      btn.classList.remove('text-slate-400', 'border-transparent');

      // Update visible doc panel
      docPanels.forEach(panel => {
        if (panel.id === targetId) {
          panel.classList.remove('hidden');
        } else {
          panel.classList.add('hidden');
        }
      });
    });
  });
}

/**
 * Image Lightbox Modal for Screenshots
 */
function setupLightbox() {
  const modal = document.getElementById('lightbox-modal');
  const modalImg = document.getElementById('lightbox-image');
  const modalCaption = document.getElementById('lightbox-caption');
  const closeBtn = document.getElementById('lightbox-close');

  if (!modal || !modalImg) return;

  document.querySelectorAll('.zoomable-image').forEach(img => {
    img.addEventListener('click', () => {
      modalImg.src = img.src;
      modalCaption.textContent = img.alt || 'Screenshot Preview';
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
    });
  });

  const closeModal = () => {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  };

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal || e.target.classList.contains('lightbox-backdrop')) {
      closeModal();
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('active')) {
      closeModal();
    }
  });
}

/**
 * Copy to clipboard utility for code snippets
 */
function setupCodeCopyButtons() {
  document.querySelectorAll('.copy-code-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const targetSelector = btn.getAttribute('data-clipboard-target');
      const targetEl = document.querySelector(targetSelector);
      if (!targetEl) return;

      const codeText = targetEl.innerText || targetEl.textContent;
      try {
        await navigator.clipboard.writeText(codeText.trim());
        const originalText = btn.innerHTML;
        btn.innerHTML = `
          <svg class="w-4 h-4 text-emerald-400 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path>
          </svg>
          <span class="text-emerald-400 text-xs">Copied!</span>
        `;
        setTimeout(() => {
          btn.innerHTML = originalText;
        }, 2200);
      } catch (err) {
        console.error("Clipboard copy failed:", err);
      }
    });
  });
}

/**
 * FAQ Collapsible Accordions
 */
function setupFAQAccordion() {
  document.querySelectorAll('.faq-trigger').forEach(trigger => {
    trigger.addEventListener('click', () => {
      const content = trigger.nextElementSibling;
      const arrow = trigger.querySelector('.faq-arrow');

      const isOpen = !content.classList.contains('hidden');
      if (isOpen) {
        content.classList.add('hidden');
        if (arrow) arrow.classList.remove('rotate-180');
      } else {
        content.classList.remove('hidden');
        if (arrow) arrow.classList.add('rotate-180');
      }
    });
  });
}
