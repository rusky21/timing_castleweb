import React, { useEffect, useRef, useCallback } from 'react';
import './TheoShowcase.css';

const CARDS_COUNT = 5;
const REPEAT_COUNT = 4;
const TOTAL_CARDS = CARDS_COUNT * REPEAT_COUNT;

export const TheoShowcase: React.FC = () => {
  const sectionRef = useRef<HTMLElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const trackRef = useRef<HTMLDivElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);

  // Interaction State
  const isPlaying = true;

  // Physics & Animation Refs (run in requestAnimationFrame without React re-rendering)
  const animRef = useRef<number | null>(null);
  const scrollPosRef = useRef<number>(0);
  const velocityRef = useRef<number>(0);
  const isDraggingRef = useRef<boolean>(false);
  const isHoveredRef = useRef<boolean>(false);
  const autoSpeedRef = useRef<number>(0.85);

  // Pointer drag
  const pointerStartXRef = useRef<number>(0);
  const pointerStartYRef = useRef<number>(0);
  const lastPointerXRef = useRef<number>(0);
  const lastTimeRef = useRef<number>(0);
  const hasMovedSignificantRef = useRef<boolean>(false);

  // Programmatic targeting
  const targetScrollPosRef = useRef<number | null>(null);

  // Center card tracking without React re-renders
  const lastActiveIndexRef = useRef<number>(2);

  // Window scroll parallax & entrance smoothing
  const lastWindowScrollYRef = useRef<number>(0);
  const targetProgressRef = useRef<number>(0);
  const smoothProgressRef = useRef<number>(0);
  const isSectionInViewRef = useRef<boolean>(false);

  // Responsive measurements
  const dimsRef = useRef<{
    containerWidth: number;
    cardWidth: number;
    cardHeight: number;
    gap: number;
    stride: number;
    setPeriod: number;
    totalTrackWidth: number;
  }>({
    containerWidth: 1600,
    cardWidth: 350,
    cardHeight: 470,
    gap: 22,
    stride: 372,
    setPeriod: 372 * 5,
    totalTrackWidth: 372 * TOTAL_CARDS,
  });

  // Calculate layout dimensions
  const updateDims = useCallback(() => {
    if (!containerRef.current) return;
    const w = containerRef.current.clientWidth || window.innerWidth;
    
    // Scale card dimensions dynamically based on viewport
    let cardW = 350;
    let gap = 24;

    if (w >= 1600) {
      cardW = Math.min(380, Math.round(w * 0.21));
      gap = 24;
    } else if (w >= 1200) {
      cardW = Math.round(w * 0.23);
      gap = 20;
    } else if (w >= 768) {
      cardW = Math.round(w * 0.32);
      gap = 16;
    } else {
      cardW = Math.round(w * 0.62);
      gap = 14;
    }

    const cardH = Math.round(cardW * 1.25);
    const stride = cardW + gap;
    const setPeriod = stride * CARDS_COUNT;
    const totalTrackWidth = stride * TOTAL_CARDS;

    dimsRef.current = {
      containerWidth: w,
      cardWidth: cardW,
      cardHeight: cardH,
      gap,
      stride,
      setPeriod,
      totalTrackWidth,
    };
  }, []);

  // Update card 3D transforms along the arched ribbon
  const renderFrame = useCallback((enterProgress: number) => {
    const { containerWidth, cardWidth, cardHeight, stride, totalTrackWidth } = dimsRef.current;
    if (containerWidth <= 0) return;

    let scrollPos = scrollPosRef.current;
    const centerX = containerWidth / 2;
    // Span over which cards arc (half-width of arch)
    const span = Math.max(300, containerWidth * 0.46);
    // Vertical dip at the center of the arch (controlled elegant dip)
    const maxDip = Math.min(30, Math.max(14, containerWidth * 0.018));

    // Smooth entrance effects applied to the stage container:
    // As user scrolls onto the block (enterProgress 0 -> 1), stage smoothly unfolds
    if (trackRef.current) {
      const stageScale = 0.96 + 0.04 * Math.min(1, enterProgress * 1.35);
      const stageOpacity = Math.min(1, enterProgress * 2.2);
      trackRef.current.style.transform = `translate3d(0, 0, 0) scale(${stageScale.toFixed(3)})`;
      trackRef.current.style.opacity = `${stageOpacity.toFixed(2)}`;
    }

    if (bottomRef.current) {
      const bottomEntranceY = (1 - Math.min(1, Math.max(0, (enterProgress - 0.22) * 1.8))) * 20;
      const bottomOpacity = Math.min(1, Math.max(0, (enterProgress - 0.18) * 2.2));
      bottomRef.current.style.transform = `translate3d(0, ${bottomEntranceY.toFixed(1)}px, 0)`;
      bottomRef.current.style.opacity = `${bottomOpacity.toFixed(2)}`;
    }

    let closestDist = Infinity;
    let closestIndex = 0;

    for (let i = 0; i < TOTAL_CARDS; i++) {
      const cardEl = cardRefs.current[i];
      if (!cardEl) continue;

      // Base offset of this card along the infinite track
      const rawX = i * stride - scrollPos;
      // Wrap relative to center
      let relX = ((rawX % totalTrackWidth) + totalTrackWidth) % totalTrackWidth;
      if (relX > totalTrackWidth / 2) relX -= totalTrackWidth;

      // Normalized distance from center u in [-1..1]
      const u = relX / span;
      const absU = Math.abs(u);

      // Track the card closest to center
      if (Math.abs(relX) < closestDist) {
        closestDist = Math.abs(relX);
        closestIndex = i % CARDS_COUNT;
      }

      // Parabolic vertical dip arch (dips in the center, lifts at edges)
      const archFactor = Math.max(0, 1 - Math.pow(Math.min(1.2, absU * 0.95), 2));
      const archY = archFactor * maxDip;

      // Scale: center card is ~0.84, edges are ~1.00
      const scaleFactor = 0.84 + 0.16 * Math.min(1.12, Math.pow(absU, 1.35));

      // 3D Rotation on Y axis (concave cylinder curve)
      const clampedU = Math.max(-1.5, Math.min(1.5, u));
      const rotateY = -clampedU * 22;

      // Rotation on Z axis (tangent along the arched smile curve)
      const rotateZ = clampedU * 4.2;

      // Z depth: center card is set back slightly into screen
      const zDepth = -archFactor * 48;

      // Opacity: smoothly fade out cards beyond visible sides
      const opacity = absU > 1.35 ? Math.max(0, 1 - (absU - 1.35) / 0.3) : 1;

      // Visibility optimization
      if (opacity <= 0.01) {
        cardEl.style.visibility = 'hidden';
      } else {
        cardEl.style.visibility = 'visible';
        cardEl.style.opacity = `${opacity}`;
        cardEl.style.width = `${cardWidth}px`;
        cardEl.style.height = `${cardHeight}px`;

        // Direct hardware-accelerated transform
        const cardLeft = centerX + relX - cardWidth / 2;
        cardEl.style.transform = `translate3d(${cardLeft.toFixed(1)}px, ${archY.toFixed(1)}px, ${zDepth.toFixed(1)}px) rotateY(${rotateY.toFixed(2)}deg) rotateZ(${rotateZ.toFixed(2)}deg) scale(${scaleFactor.toFixed(3)})`;
        cardEl.style.zIndex = `${Math.round(100 - absU * 20)}`;
      }
    }

    // Direct DOM class updates for active center card (0 React re-renders while animating!)
    if (lastActiveIndexRef.current !== closestIndex) {
      lastActiveIndexRef.current = closestIndex;
      for (let i = 0; i < TOTAL_CARDS; i++) {
        const el = cardRefs.current[i];
        if (el) {
          if ((i % CARDS_COUNT) === closestIndex) {
            el.classList.add('is-active-center');
          } else {
            el.classList.remove('is-active-center');
          }
        }
      }
    }
  }, []);

  // Main animation loop
  useEffect(() => {
    updateDims();
    window.addEventListener('resize', updateDims);

    // Initial center offset: position project 3 (index 2) in the center
    const { stride } = dimsRef.current;
    scrollPosRef.current = 2 * stride;

    // Window scroll listener for smooth parallax & viewport entry
    lastWindowScrollYRef.current = window.scrollY;

    const handleWindowScroll = () => {
      const currentY = window.scrollY;
      const dy = currentY - lastWindowScrollYRef.current;
      lastWindowScrollYRef.current = currentY;

      if (!sectionRef.current) return;
      const rect = sectionRef.current.getBoundingClientRect();
      const vh = window.innerHeight;

      // Check if block is near viewport
      const inView = rect.top < vh + 150 && rect.bottom > -150;
      isSectionInViewRef.current = inView;

      if (inView) {
        // Entry progress: 0 when top is at bottom of viewport, 1 when section is centered
        const enterProgress = Math.max(0, Math.min(1, (vh - rect.top) / (vh * 0.75)));
        targetProgressRef.current = enterProgress;

        // Smoothly couple page scroll with horizontal carousel glide
        if (Math.abs(dy) > 0.2) {
          const scrollImpulse = dy * 0.07;
          velocityRef.current = Math.max(-24, Math.min(24, velocityRef.current + scrollImpulse));
        }
      }
    };

    handleWindowScroll();
    window.addEventListener('scroll', handleWindowScroll, { passive: true });

    const tick = () => {
      const { totalTrackWidth } = dimsRef.current;

      // 1. Smoothly interpolate section entrance progress with buttery LERP
      smoothProgressRef.current += (targetProgressRef.current - smoothProgressRef.current) * 0.085;
      const enterP = smoothProgressRef.current;

      // 2. Smooth auto-play transition (gradual deceleration on hover, gradual resume on leave)
      let targetAutoSpeed = 0;
      if (isPlaying && !isHoveredRef.current && !isDraggingRef.current) {
        targetAutoSpeed = 0.85;
      }
      autoSpeedRef.current += (targetAutoSpeed - autoSpeedRef.current) * 0.05;

      // 3. Movement integration
      if (targetScrollPosRef.current !== null) {
        // Smooth programmatic scroll to target card
        const diff = targetScrollPosRef.current - scrollPosRef.current;
        if (Math.abs(diff) > 0.3) {
          scrollPosRef.current += diff * 0.085;
        } else {
          scrollPosRef.current = targetScrollPosRef.current;
          targetScrollPosRef.current = null;
        }
      } else if (isDraggingRef.current) {
        // Handled in pointermove
      } else {
        // Smooth friction momentum deceleration (never abrupt stops!)
        if (Math.abs(velocityRef.current) > 0.01) {
          scrollPosRef.current += velocityRef.current;
          velocityRef.current *= 0.935;
        } else {
          velocityRef.current = 0;
        }
        // Smooth auto-glide
        scrollPosRef.current += autoSpeedRef.current;
      }

      // 4. Modulo wrap at totalTrackWidth (20 cards) -> 100% mathematically continuous, no visible card jumps!
      if (totalTrackWidth > 0) {
        if (scrollPosRef.current >= totalTrackWidth) {
          scrollPosRef.current -= totalTrackWidth;
          if (targetScrollPosRef.current !== null) {
            targetScrollPosRef.current -= totalTrackWidth;
          }
        } else if (scrollPosRef.current < 0) {
          scrollPosRef.current += totalTrackWidth;
          if (targetScrollPosRef.current !== null) {
            targetScrollPosRef.current += totalTrackWidth;
          }
        }
      }

      renderFrame(enterP);
      animRef.current = requestAnimationFrame(tick);
    };

    animRef.current = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener('resize', updateDims);
      window.removeEventListener('scroll', handleWindowScroll);
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [updateDims, renderFrame, isPlaying]);

  // Pointer Drag Handlers (Mouse & Touch)
  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    isDraggingRef.current = true;
    containerRef.current?.classList.add('is-dragging');
    targetScrollPosRef.current = null;
    velocityRef.current = 0;
    pointerStartXRef.current = e.clientX;
    pointerStartYRef.current = e.clientY;
    lastPointerXRef.current = e.clientX;
    lastTimeRef.current = performance.now();
    hasMovedSignificantRef.current = false;

    // Capture pointer events
    if (e.currentTarget) {
      e.currentTarget.setPointerCapture(e.pointerId);
    }
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isDraggingRef.current) return;

    const now = performance.now();
    const dt = Math.max(1, now - lastTimeRef.current);
    const deltaX = e.clientX - lastPointerXRef.current;

    if (Math.abs(e.clientX - pointerStartXRef.current) > 5) {
      hasMovedSignificantRef.current = true;
    }

    // Scroll with drag
    scrollPosRef.current -= deltaX;

    // Instantaneous velocity (px per ~16ms frame)
    velocityRef.current = -(deltaX / dt) * 16;
    // Limit max fling velocity
    velocityRef.current = Math.max(-28, Math.min(28, velocityRef.current));

    lastPointerXRef.current = e.clientX;
    lastTimeRef.current = now;
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isDraggingRef.current) return;
    isDraggingRef.current = false;
    containerRef.current?.classList.remove('is-dragging');

    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      // Ignore if already released
    }
  };

  // Wheel Horizontal & Vertical Momentum Support (Zero jerkiness, smooth physics)
  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    const isHorizontal = Math.abs(e.deltaX) > Math.abs(e.deltaY) || e.shiftKey;
    const delta = isHorizontal ? (e.shiftKey ? e.deltaY : e.deltaX) : e.deltaY;

    if (Math.abs(delta) > 1) {
      // Add smooth momentum impulse instead of instant position teleportation!
      // This eliminates 100% of the jerky "stepped" jumps
      const factor = isHorizontal ? 0.055 : 0.035;
      const impulse = delta * factor;
      
      velocityRef.current = Math.max(-26, Math.min(26, velocityRef.current + impulse));
      targetScrollPosRef.current = null;
    }
  };

  // Click card to smoothly center it in view
  const handleCardClick = (index: number) => {
    if (hasMovedSignificantRef.current) return; // Ignore clicks if user dragged

    const { stride, totalTrackWidth } = dimsRef.current;
    if (stride <= 0 || totalTrackWidth <= 0) return;

    const target = index * stride;

    // Choose shortest path along the infinite wrap track
    let diff = target - scrollPosRef.current;
    diff = ((diff % totalTrackWidth) + totalTrackWidth * 1.5) % totalTrackWidth - totalTrackWidth * 0.5;
    targetScrollPosRef.current = scrollPosRef.current + diff;
  };

  return (
    <section className="theo-showcase-section" id="showcase" ref={sectionRef}>
      {/* --- Top 3D Curved Cards Interactive Ribbon --- */}
      <div
        className="showcase-cards-wrapper"
        ref={containerRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onWheel={handleWheel}
        onMouseEnter={() => {
          isHoveredRef.current = true;
        }}
        onMouseLeave={() => {
          isHoveredRef.current = false;
        }}
        role="region"
        aria-label="Интерактивные 3D карточки кейсов"
      >
        {/* Track containing 3D positioned cards */}
        <div className="showcase-cards-stage" ref={trackRef}>
          {Array.from({ length: TOTAL_CARDS }).map((_, index) => {
            const isCenterInitially = (index % CARDS_COUNT) === 2;

            return (
              <div
                key={`card-${index}`}
                ref={(el) => {
                  cardRefs.current[index] = el;
                }}
                className={`showcase-card ${isCenterInitially ? 'is-active-center' : ''}`}
                onClick={() => handleCardClick(index)}
                role="button"
                tabIndex={0}
                aria-label={`Кейс ${(index % CARDS_COUNT) + 1}`}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    handleCardClick(index);
                  }
                }}
              >
                {/* Sleek card shell with visual preview */}
                <div className="card-media-shell">
                  <img
                    src={`/assets/showcase/card${(index % CARDS_COUNT) + 1}.png`}
                    alt={`Кейс ${(index % CARDS_COUNT) + 1}`}
                    className="card-media-image"
                    loading="lazy"
                    draggable={false}
                  />
                  <div className="card-empty-surface">
                    <div className="card-empty-grid" />
                    <div className="card-empty-corners" />
                    <div className="card-sheen-overlay" />
                    <div className="card-vignette" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* --- Bottom Showcase Info Bar --- */}
      <div className="showcase-bottom reveal-void delay-150" ref={bottomRef}>
        <h2 className="theo-heading">КЕЙСЫ</h2>

        <div className="showcase-right-col">
          <a
            href="#showcase"
            className="connect-badge"
            aria-label="Посмотреть работы"
            onClick={(e) => {
              e.preventDefault();
              if (containerRef.current) {
                containerRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }
            }}
          >
            <span className="reticle-dot dot-tl" aria-hidden="true" />
            <span className="reticle-dot dot-tr" aria-hidden="true" />
            <span className="reticle-dot dot-bl" aria-hidden="true" />
            <span className="reticle-dot dot-br" aria-hidden="true" />
            <span className="connect-text">ПОСМОТРЕТЬ РАБОТЫ</span>
          </a>

          <p className="showcase-description reveal-void delay-200">
            Мы не просто пишем код, а решаем реальные задачи бизнеса. Проектируем и запускаем сложные веб-сервисы с нуля, усиливаем существующие команды и консультируем фаундеров, как грамотно и без лишних затрат реализовать продукт в цифровой среде.
          </p>
        </div>
      </div>

    </section>
  );
};

export default TheoShowcase;
