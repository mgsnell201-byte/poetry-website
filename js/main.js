document.addEventListener('DOMContentLoaded', () => {
  // Mobile navigation toggle
  const menuBtn = document.querySelector('.menu-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (menuBtn && navLinks) {
    menuBtn.addEventListener('click', () => {
      navLinks.classList.toggle('open');
    });
  }

  // Inline track row play/pause
  const audio = new Audio();
  let activeBtn = null;
  let isPlaying = false;

  const stopPlayback = () => {
    audio.pause();
    isPlaying = false;
    document.querySelectorAll('.track-row').forEach((r) => r.classList.remove('is-playing'));
    document.querySelectorAll('.track-row .play-btn').forEach((b) => (b.textContent = '▶'));
  };

  document.querySelectorAll('.track-row .play-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const row = btn.closest('.track-row');
      const src = row?.dataset.src || '';
      if (!src) return;

      if (activeBtn === btn && isPlaying) {
        stopPlayback();
        return;
      }

      stopPlayback();
      activeBtn = btn;
      row?.classList.add('is-playing');
      audio.src = src;
      audio.play().then(() => {
        isPlaying = true;
        btn.textContent = '❚❚';
      }).catch(() => {
        stopPlayback();
      });
    });
  });

  audio.addEventListener('ended', stopPlayback);

  // Web3Forms Comment Submission
  const form = document.getElementById('comment-form');
  const status = document.getElementById('comment-status');
  if (!form || !status) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalLabel = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending...';
    status.className = 'form-status';
    status.textContent = '';

    try {
      const formData = new FormData(form);
      const res = await fetch('https://api.web3forms.com/submit', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok && data.success) {
        status.className = 'form-status is-success';
        status.textContent = 'Thank you — your comment has been sent.';
        form.reset();
      } else {
        status.className = 'form-status is-error';
        status.textContent = data.message || 'Could not send comment. Please try again.';
      }
    } catch (_) {
      status.className = 'form-status is-error';
      status.textContent = 'Could not reach Web3Forms (note: some browsers block form requests from file://; it will work once hosted).';
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = originalLabel;
    }
  });
});


// Archive Grid Pagination (12 items per page)
document.addEventListener('DOMContentLoaded', () => {
  const grid = document.querySelector('.media-grid[data-page-size]');
  const nav = document.getElementById('archive-pagination');
  if (!grid || !nav) return;

  const pageSize = parseInt(grid.dataset.pageSize || '12', 10);
  const cards = Array.from(grid.querySelectorAll('.media-card'));
  const totalPages = Math.ceil(cards.length / pageSize);
  if (totalPages <= 1) return;

  const prevBtn = document.getElementById('page-prev');
  const nextBtn = document.getElementById('page-next');
  const statusEl = document.getElementById('page-status');
  let currentPage = 1;

  const renderPage = (page) => {
    currentPage = Math.max(1, Math.min(totalPages, page));
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    cards.forEach((card, i) => {
      card.style.display = i >= start && i < end ? '' : 'none';
    });
    statusEl.textContent = `Page ${currentPage} of ${totalPages}`;
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === totalPages;
  };

  nav.hidden = false;
  prevBtn.addEventListener('click', () => {
    renderPage(currentPage - 1);
    grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  nextBtn.addEventListener('click', () => {
    renderPage(currentPage + 1);
    grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  renderPage(1);
});
