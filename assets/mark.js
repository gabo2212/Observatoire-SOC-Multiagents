import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

const canvas = document.querySelector("#mark");
if (!canvas) throw new Error("missing canvas");

const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const MAX_EDGE = 960;

let renderer;
try {
  renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,
    antialias: false,
    powerPreference: "high-performance",
  });
} catch (err) {
  canvas.hidden = true;
  throw err;
}

renderer.setPixelRatio(1);
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 40);
camera.position.set(0.15, 0.05, 6.4);

const material = new THREE.ShaderMaterial({
  toneMapped: false,
  vertexShader: `
    varying vec3 vNormal;
    varying vec3 vViewPosition;

    void main() {
      vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
      vNormal = normalize(normalMatrix * normal);
      vViewPosition = -mvPosition.xyz;
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  fragmentShader: `
    varying vec3 vNormal;
    varying vec3 vViewPosition;

    void main() {
      float ndv = clamp(dot(normalize(vNormal), normalize(vViewPosition)), 0.0, 1.0);
      float fres = pow(1.0 - ndv, 1.4);
      vec3 film = 0.55 + 0.45 * cos(6.28318 * (fres * 1.8 + vec3(0.0, 0.33, 0.67)));
      vec3 pale = vec3(0.96, 0.965, 0.97);
      float rim = smoothstep(0.02, 0.78, fres);
      gl_FragColor = vec4(mix(pale, film, rim), 1.0);
    }
  `,
});

const arm = new RoundedBoxGeometry(0.58, 2.72, 0.78, 2, 0.14);
const mark = new THREE.Group();
for (let i = 0; i < 3; i += 1) {
  const mesh = new THREE.Mesh(arm, material);
  mesh.rotation.z = (i * Math.PI) / 3;
  mark.add(mesh);
}
mark.scale.setScalar(0.46);
mark.position.y = -0.2;
mark.rotation.x = 0.7;
mark.rotation.z = -0.22;
scene.add(mark);

let targetX = 0;
let targetY = 0;
window.addEventListener("pointermove", (event) => {
  if (reduced) return;
  targetX = (event.clientX / window.innerWidth - 0.5) * 0.55;
  targetY = (event.clientY / window.innerHeight - 0.5) * 0.22;
});

let viewW = 0;
let viewH = 0;

function resize() {
  const cssW = canvas.clientWidth;
  const cssH = canvas.clientHeight;
  if (!cssW || !cssH) return;

  const longest = Math.max(cssW, cssH);
  const scale = longest > MAX_EDGE ? MAX_EDGE / longest : 1;
  const width = Math.max(1, Math.round(cssW * scale));
  const height = Math.max(1, Math.round(cssH * scale));
  if (width === viewW && height === viewH) return;

  viewW = width;
  viewH = height;
  renderer.setSize(width, height, false);
  camera.aspect = cssW / cssH;
  camera.updateProjectionMatrix();
  if (!raf) renderer.render(scene, camera);
}

const frame = new ResizeObserver(resize);
frame.observe(canvas);

let spin = 0;
let raf = 0;
let visible = true;

function renderFrame() {
  if (document.hidden || !visible) {
    raf = 0;
    return;
  }
  spin += 0.004;
  mark.rotation.y += (spin * 0.35 + targetX - mark.rotation.y) * 0.06;
  mark.rotation.x += (0.7 + targetY - mark.rotation.x) * 0.06;
  renderer.render(scene, camera);
  raf = requestAnimationFrame(renderFrame);
}

function play() {
  if (reduced || raf || document.hidden || !visible) return;
  raf = requestAnimationFrame(renderFrame);
}

function pause() {
  if (!raf) return;
  cancelAnimationFrame(raf);
  raf = 0;
}

document.addEventListener("visibilitychange", () => {
  if (document.hidden) pause();
  else play();
});

const hero = canvas.closest(".hero") || canvas;
const visibility = new IntersectionObserver((entries) => {
  const entry = entries[entries.length - 1];
  visible = entry.isIntersecting;
  if (visible) play();
  else pause();
});
visibility.observe(hero);

resize();
if (!raf) renderer.render(scene, camera);
play();
