const initHeroScene = () => {
  const canvas = document.getElementById('hero-canvas');
  const container = canvas?.parentElement;
  if (!canvas || !container || typeof THREE === 'undefined') return;
  const mode = canvas.dataset.mode || 'all';

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  camera.position.set(0, 0, 8.5);

  const syncVisualWidth = () => {
    const navLinks = document.querySelector('.nav-links');
    if (window.innerWidth > 768 && navLinks) {
      const w = navLinks.getBoundingClientRect().width;
      if (w > 0) container.style.width = `${Math.round(w)}px`;
    } else {
      container.style.width = '';
    }
  };

  const resize = () => {
    syncVisualWidth();
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  resize();
  window.addEventListener('load', resize);
  document.fonts?.ready.then(resize);
  window.addEventListener('resize', resize);
  const navEl = document.querySelector('.nav-links');
  if (navEl && typeof ResizeObserver !== 'undefined') new ResizeObserver(resize).observe(navEl);

  // Lighting
  scene.add(new THREE.AmbientLight(0xede8df, 0.95));
  const keyLight = new THREE.DirectionalLight(0xc59b5f, 1.5);
  keyLight.position.set(4, 6, 5);
  scene.add(keyLight);

  const brassMat = new THREE.MeshStandardMaterial({
    color: 0xc59b5f,
    metalness: 0.55,
    roughness: 0.35,
  });
  const rimMat = new THREE.MeshStandardMaterial({
    color: 0xede8df,
    metalness: 0.25,
    roughness: 0.45,
  });

  const createNote = (beamed) => {
    const group = new THREE.Group();
    const headGeo = new THREE.SphereGeometry(0.11, 16, 12);
    headGeo.scale(1.25, 0.9, 0.7);
    const stemGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.52, 8);

    const head1 = new THREE.Mesh(headGeo, brassMat);
    head1.rotation.z = 0.35;
    group.add(head1);

    const stem1 = new THREE.Mesh(stemGeo, brassMat);
    stem1.position.set(0.09, 0.25, 0);
    group.add(stem1);

    if (beamed) {
      const head2 = new THREE.Mesh(headGeo, brassMat);
      head2.position.set(0.32, -0.05, 0);
      head2.rotation.z = 0.35;
      group.add(head2);

      const stem2 = new THREE.Mesh(stemGeo, brassMat);
      stem2.position.set(0.41, 0.2, 0);
      group.add(stem2);

      const beam = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.055, 0.03), brassMat);
      beam.position.set(0.25, 0.48, 0);
      beam.rotation.z = -0.14;
      group.add(beam);
    } else {
      const flag = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.045, 0.025), brassMat);
      flag.position.set(0.17, 0.46, 0);
      flag.rotation.z = -0.55;
      group.add(flag);
    }

    return group;
  };

  // Pages (for 'all' and 'pages' modes)
  const pages = [];
  if (mode === 'all') {
    const makePageTexture = () => {
      const c = document.createElement('canvas');
      c.width = 256;
      c.height = 320;
      const ctx = c.getContext('2d');
      ctx.fillStyle = '#ede8df';
      ctx.fillRect(0, 0, c.width, c.height);
      ctx.strokeStyle = 'rgba(18, 17, 16, 0.18)';
      ctx.lineWidth = 2;
      for (let y = 44; y < 285; y += 22) {
        ctx.beginPath();
        ctx.moveTo(28, y);
        ctx.lineTo(228 - ((y * 13) % 55), y);
        ctx.stroke();
      }
      ctx.strokeStyle = 'rgba(197, 155, 95, 0.55)';
      ctx.strokeRect(8, 8, c.width - 16, c.height - 16);
      const tex = new THREE.CanvasTexture(c);
      tex.colorSpace = THREE.SRGBColorSpace;
      return tex;
    };

    const pageMat = new THREE.MeshStandardMaterial({
      map: makePageTexture(),
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.78,
      roughness: 0.85,
    });

    const pageGeo = new THREE.PlaneGeometry(1.15, 1.45, 10, 12);
    const pos = pageGeo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const y = pos.getY(i);
      pos.setZ(i, Math.sin(x * 2.1) * 0.1 + Math.cos(y * 1.4) * 0.06);
    }
    pageGeo.computeVertexNormals();

    for (let i = 0; i < 6; i++) {
      const mesh = new THREE.Mesh(pageGeo, pageMat);
      const base = {
        x: (Math.random() - 0.5) * 5.2,
        y: (Math.random() - 0.5) * 3.0,
        z: mode === 'all' ? (-1.1 - Math.random() * 1.1) : ((Math.random() - 0.5) * 2.4 - 0.4),
        rx: (Math.random() - 0.5) * 0.7,
        ry: (Math.random() - 0.5) * 0.9,
        rz: (Math.random() - 0.5) * 0.5,
        speed: 0.35 + Math.random() * 0.35,
        phase: Math.random() * Math.PI * 2,
      };
      mesh.position.set(base.x, base.y, base.z);
      mesh.rotation.set(base.rx, base.ry, base.rz);
      mesh.userData = base;
      scene.add(mesh);
      pages.push(mesh);
    }
  }

  // Orbiting notes (for 'all' mode)
  const notes = [];
  if (mode === 'all') {
    for (let i = 0; i < 8; i++) {
      const note = createNote(i % 2 === 0);
      const base = {
        x: (Math.random() - 0.5) * 4.4,
        y: (Math.random() - 0.5) * 2.1,
        z: (Math.random() - 0.5) * 2.2 + 0.4,
        speed: 0.5 + Math.random() * 0.45,
        phase: Math.random() * Math.PI * 2,
      };
      note.position.set(base.x, base.y, base.z);
      note.scale.setScalar(0.85 + Math.random() * 0.35);
      note.userData = base;
      scene.add(note);
      notes.push(note);
    }
  }

  // Spinning Vinyl + Rising Notes (for 'notes' mode on Music page)
  let vinylSpinner = null;
  const risingNotes = [];
  if (mode === 'notes' || mode === 'all') {
    const vinylTilt = new THREE.Group();
    vinylTilt.position.set(0, 0, 0);
    vinylTilt.rotation.x = 0.95;
    vinylTilt.rotation.z = -0.15;
    scene.add(vinylTilt);

    vinylSpinner = new THREE.Group();
    vinylTilt.add(vinylSpinner);

    const discMat = new THREE.MeshStandardMaterial({
      color: 0x1b1917,
      metalness: 0.35,
      roughness: 0.45,
    });
    const disc = new THREE.Mesh(new THREE.CylinderGeometry(2.05, 2.05, 0.06, 64), discMat);
    vinylSpinner.add(disc);

    // Subtle brass groove rings
    [1.85, 1.55, 1.25, 0.95].forEach((r, idx) => {
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(r, 0.012, 8, 64),
        new THREE.MeshBasicMaterial({ color: 0xc59b5f, transparent: true, opacity: 0.25 + idx * 0.06 })
      );
      ring.rotation.x = Math.PI / 2;
      ring.position.y = 0.034;
      vinylSpinner.add(ring);
    });

    // Center brass label + spindle
    const label = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.62, 0.07, 48), brassMat);
    vinylSpinner.add(label);
    const spindle = new THREE.Mesh(
      new THREE.CylinderGeometry(0.06, 0.06, 0.14, 16),
      new THREE.MeshStandardMaterial({ color: 0xede8df, metalness: 0.6, roughness: 0.3 })
    );
    vinylSpinner.add(spindle);
    if (mode === 'notes') {
      const armGroup = new THREE.Group();
      armGroup.position.set(2.15, 0.22, -0.7);
      const pivot = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.22, 0.16, 24), brassMat);
      const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.032, 0.032, 1.85, 12), rimMat || new THREE.MeshStandardMaterial({ color: 0xede8df, metalness: 0.5, roughness: 0.35 }));
      arm.rotation.z = Math.PI / 2;
      arm.rotation.y = 0.42;
      arm.position.set(-0.78, 0.05, 0.35);
      const head = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.08, 0.14), brassMat);
      head.position.set(-1.55, 0.02, 0.7);
      head.rotation.y = 0.42;
      armGroup.add(pivot, arm, head);
      vinylTilt.add(armGroup);
    }

    // Notes rising smoothly from the spinning record (on Music page)
    if (false) {
      for (let i = 0; i < 6; i++) {
      const note = createNote(i % 2 === 0);
      note.scale.setScalar(0.7 + (i % 3) * 0.12);
      note.userData = {
        offset: i / 6,
        radius: 0.55 + (i % 3) * 0.45,
        angle: (i / 6) * Math.PI * 2,
        speed: 0.24 + (i % 2) * 0.06,
      };
        scene.add(note);
        risingNotes.push(note);
      }
    }
  }

  // 3D Extruded Fountain Pen Nib (for 'pages' mode on Poetry page)
  let nibGroup = null;
  if (mode === 'pages') {
    nibGroup = new THREE.Group();
    const nibShape = new THREE.Shape();
    nibShape.moveTo(0, 1.45);
    nibShape.lineTo(0.22, 0.55);
    nibShape.quadraticCurveTo(0.75, 0.1, 0.52, -0.85);
    nibShape.lineTo(0.36, -1.28);
    nibShape.lineTo(-0.36, -1.28);
    nibShape.lineTo(-0.52, -0.85);
    nibShape.quadraticCurveTo(-0.75, 0.1, -0.22, 0.55);
    nibShape.closePath();

    const hole = new THREE.Path();
    hole.absarc(0, 0.12, 0.11, 0, Math.PI * 2, true);
    nibShape.holes.push(hole);

    const nibGeo = new THREE.ExtrudeGeometry(nibShape, {
      depth: 0.12,
      bevelEnabled: true,
      bevelThickness: 0.03,
      bevelSize: 0.03,
      bevelSegments: 2,
    });
    nibGeo.center();
    const nibMesh = new THREE.Mesh(nibGeo, brassMat);

    // Center slit + collar band
    const slit = new THREE.Mesh(new THREE.BoxGeometry(0.025, 1.15, 0.18), new THREE.MeshBasicMaterial({ color: 0x121110 }));
    slit.position.set(0, 0.72, 0);
    const collar = new THREE.Mesh(new THREE.BoxGeometry(0.82, 0.14, 0.2), rimMat);
    collar.position.set(0, -1.08, 0);

    nibGroup.add(nibMesh, slit, collar);
    nibGroup.rotation.z = -0.22;
    nibGroup.scale.setScalar(0.95);
    scene.add(nibGroup);
  }

  // 3D Extruded Shield with Checkmark (for 'privacy' mode)
  let sealGroup = null;
  if (mode === 'privacy') {
    sealGroup = new THREE.Group();

    const makeShieldShape = (s) => {
      const sh = new THREE.Shape();
      sh.moveTo(0, 1.35 * s);
      sh.quadraticCurveTo(0.48 * s, 1.05 * s, 1.05 * s, 1.02 * s);
      sh.bezierCurveTo(1.12 * s, 0.15 * s, 0.82 * s, -0.78 * s, 0, -1.35 * s);
      sh.bezierCurveTo(-0.82 * s, -0.78 * s, -1.12 * s, 0.15 * s, -1.05 * s, 1.02 * s);
      sh.quadraticCurveTo(-0.48 * s, 1.05 * s, 0, 1.35 * s);
      return sh;
    };

    const outerGeo = new THREE.ExtrudeGeometry(makeShieldShape(1.0), {
      depth: 0.12,
      bevelEnabled: true,
      bevelThickness: 0.03,
      bevelSize: 0.03,
      bevelSegments: 2,
    });
    outerGeo.center();
    const outerShield = new THREE.Mesh(outerGeo, rimMat);

    const innerGeo = new THREE.ExtrudeGeometry(makeShieldShape(0.84), {
      depth: 0.18,
      bevelEnabled: true,
      bevelThickness: 0.02,
      bevelSize: 0.02,
      bevelSegments: 2,
    });
    innerGeo.center();
    const innerShield = new THREE.Mesh(innerGeo, brassMat);

    const checkShape = new THREE.Shape();
    checkShape.moveTo(-0.42, 0.02);
    checkShape.lineTo(-0.28, 0.16);
    checkShape.lineTo(-0.08, -0.04);
    checkShape.lineTo(0.32, 0.36);
    checkShape.lineTo(0.46, 0.22);
    checkShape.lineTo(-0.08, -0.32);
    checkShape.closePath();

    const checkGeo = new THREE.ExtrudeGeometry(checkShape, {
      depth: 0.24,
      bevelEnabled: false,
    });
    checkGeo.center();
    const checkMesh = new THREE.Mesh(checkGeo, rimMat);

    sealGroup.add(outerShield, innerShield, checkMesh);
    sealGroup.scale.setScalar(1.05);
    scene.add(sealGroup);
  }

  // Subtle warm motes
  const moteCount = 60;
  const motePos = new Float32Array(moteCount * 3);
  for (let i = 0; i < moteCount; i++) {
    motePos[i * 3] = (Math.random() - 0.5) * 8;
    motePos[i * 3 + 1] = (Math.random() - 0.5) * 5;
    motePos[i * 3 + 2] = (Math.random() - 0.5) * 4;
  }
  const moteGeo = new THREE.BufferGeometry();
  moteGeo.setAttribute('position', new THREE.BufferAttribute(motePos, 3));
  const moteMat = new THREE.PointsMaterial({
    color: 0xc59b5f,
    size: 0.045,
    transparent: true,
    opacity: 0.55,
  });
  const motes = new THREE.Points(moteGeo, moteMat);
  scene.add(motes);

  // Subtle mouse parallax
  let targetX = 0;
  let targetY = 0;
  container.addEventListener('pointermove', (e) => {
    const rect = container.getBoundingClientRect();
    targetX = ((e.clientX - rect.left) / rect.width - 0.5) * 0.9;
    targetY = -((e.clientY - rect.top) / rect.height - 0.5) * 0.6;
  });
  container.addEventListener('pointerleave', () => {
    targetX = 0;
    targetY = 0;
  });

  const clock = new THREE.Clock();
  const animate = () => {
    requestAnimationFrame(animate);
    const t = clock.getElapsedTime();

    pages.forEach((p) => {
      const d = p.userData;
      p.position.y = d.y + Math.sin(t * d.speed + d.phase) * 0.22;
      p.rotation.x = d.rx + Math.sin(t * d.speed * 0.7 + d.phase) * 0.14;
      p.rotation.y = d.ry + Math.cos(t * d.speed * 0.6 + d.phase) * 0.18;
    });

    notes.forEach((n) => {
      const d = n.userData;
      n.position.y = d.y + Math.sin(t * d.speed + d.phase) * 0.28;
      n.rotation.y = Math.sin(t * 0.4 + d.phase) * 0.45;
      n.rotation.z = Math.cos(t * 0.35 + d.phase) * 0.12;
    });

    if (vinylSpinner) {
      vinylSpinner.rotation.y = -t * 0.65;
    }

    risingNotes.forEach((n) => {
      const d = n.userData;
      const life = (t * d.speed + d.offset) % 1;
      const a = d.angle + t * 0.4;
      n.position.x = Math.cos(a) * d.radius;
      n.position.y = -0.3 + life * 2.1;
      n.position.z = Math.sin(a) * 0.6 + 0.3;
      n.rotation.y = Math.sin(t * 0.6 + d.offset * 6) * 0.35;
      const s = 0.75 * Math.sin(life * Math.PI);
      n.scale.setScalar(Math.max(0.001, s));
    });

    if (nibGroup) {
      nibGroup.rotation.y = Math.sin(t * 0.75) * 0.45;
      nibGroup.rotation.x = Math.sin(t * 0.45) * 0.1;
    }

    if (sealGroup) {
      sealGroup.rotation.y = Math.sin(t * 0.75) * 0.48;
      sealGroup.rotation.x = Math.sin(t * 0.45) * 0.12;
    }

    motes.rotation.y = t * 0.03;

    camera.position.x += (targetX - camera.position.x) * 0.05;
    camera.position.y += (targetY - camera.position.y) * 0.05;
    camera.lookAt(0, 0, 0);

    renderer.render(scene, camera);
  };
  animate();
};

window.addEventListener('load', () => {
  let started = false;
  const start = () => {
    if (started) return;
    started = true;
    initHeroScene();
  };
  setTimeout(start, 2600);
  window.addEventListener('pointermove', start, { once: true, passive: true });
  window.addEventListener('scroll', start, { once: true, passive: true });
});
