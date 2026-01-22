import { useEffect, useRef } from 'react'

const BASE_PARTICLE_COUNT = 15  // 大幅减少粒子数量以提升性能
const TARGET_FPS = 30  // 限制帧率为 30fps
const FRAME_INTERVAL = 1000 / TARGET_FPS

const GlitterBackground = () => {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let width = window.innerWidth
    let height = window.innerHeight
    let animationFrameId
    let lastFrameTime = 0
    const floatingParticles = []
    let burstParticles = []

    const setCanvasSize = () => {
      width = window.innerWidth
      height = window.innerHeight
      const dpr = window.devicePixelRatio || 1
      canvas.width = width * dpr
      canvas.height = height * dpr
      ctx.scale(dpr, dpr)
    }

    const randomBetween = (min, max) => Math.random() * (max - min) + min
    const clamp = (value, min, max) => Math.min(Math.max(value, min), max)
    const lerp = (start, end, t) => start + (end - start) * t

    const createParticle = (overrides = {}) => ({
      x: Math.random() * width,
      y: Math.random() * height,
      size: randomBetween(0.33, 1.45),
      speedY: randomBetween(0.14, 0.44),
      drift: randomBetween(-0.065, 0.065),
      opacity: randomBetween(0.5, 0.86),
      hue: randomBetween(305, 350),
      satStart: randomBetween(55, 70),
      satEnd: randomBetween(20, 32),
      lightStart: randomBetween(92, 100),
      lightEnd: randomBetween(62, 78),
      glow: randomBetween(12, 20),
      amberCore: Math.random() > 0.5,
      flicker: randomBetween(0.02, 0.05),
      life: Infinity,
      ...overrides,
    })

    for (let i = 0; i < BASE_PARTICLE_COUNT; i += 1) {
      floatingParticles.push(createParticle())
    }

    const drawParticles = (particles) => {
      particles.forEach((particle) => {
        particle.y += particle.speedY
        particle.x += particle.drift
        particle.opacity += particle.flicker * (Math.random() > 0.5 ? 1 : -1)
        particle.opacity = Math.min(1, Math.max(0.15, particle.opacity))

        ctx.beginPath()
        const progress = clamp(particle.y / height, 0, 1)
        const saturation = lerp(particle.satStart, particle.satEnd, progress)
        const lightness = lerp(particle.lightStart, particle.lightEnd, progress)
        // 简化渐变：只使用 2 个色标以减少计算
        const gradient = ctx.createRadialGradient(
          particle.x,
          particle.y,
          0,
          particle.x,
          particle.y,
          particle.size * 3
        )
        const centerHue = particle.amberCore ? particle.hue - 20 : particle.hue
        const centerColor = `hsla(${centerHue}, ${Math.min(90, saturation + 30)}%, ${Math.min(95, lightness + 20)}%, ${Math.min(0.9, particle.opacity + 0.3)})`
        gradient.addColorStop(0, centerColor)
        gradient.addColorStop(1, `hsla(${particle.hue}, ${saturation}%, ${lightness}%, 0)`)

        // 移除阴影以提升性能
        ctx.fillStyle = gradient
        ctx.arc(particle.x, particle.y, particle.size * 2.5, 0, Math.PI * 2)
        ctx.fill()

        if (particle.y > height + 20) {
          Object.assign(particle, createParticle({ y: -10 }))
        }
        if (particle.x < -50 || particle.x > width + 50) {
          particle.x = Math.random() * width
        }
      })
    }

    const createBurstParticle = (x, y) => {
      const angle = randomBetween(-Math.PI, Math.PI)
      const speed = randomBetween(0.9, 2.4)
      return {
        x,
        y,
        size: randomBetween(1.45, 3.3),
        velocityX: Math.cos(angle) * speed * 1.2,
        velocityY: Math.sin(angle) * speed * 0.55 - randomBetween(0.15, 0.45),
        gravity: randomBetween(0.008, 0.02),
        opacity: randomBetween(0.6, 0.88),
        hue: randomBetween(310, 350),
        saturation: randomBetween(45, 68),
        lightness: randomBetween(74, 95),
        glow: randomBetween(18, 30),
        amberCore: Math.random() > 0.4,
        life: 80,
      }
    }

    const drawBurstParticles = () => {
      burstParticles = burstParticles.filter((particle) => particle.life > 0)
      burstParticles.forEach((particle) => {
        particle.x += particle.velocityX
        particle.y += particle.velocityY
        particle.velocityY += particle.gravity
        particle.opacity = Math.max(0, particle.opacity - 0.01)
        particle.life -= 1

        // 简化渐变
        const gradient = ctx.createRadialGradient(
          particle.x,
          particle.y,
          0,
          particle.x,
          particle.y,
          particle.size * 4
        )
        const burstHue = particle.amberCore ? particle.hue - 15 : particle.hue
        const burstCenterColor = `hsla(${burstHue}, ${Math.min(85, particle.saturation + 20)}%, ${Math.min(90, particle.lightness + 15)}%, ${particle.opacity * 0.8})`
        gradient.addColorStop(0, burstCenterColor)
        gradient.addColorStop(1, `hsla(${particle.hue}, ${particle.saturation}%, ${particle.lightness}%, 0)`)

        // 移除阴影以提升性能
        ctx.beginPath()
        ctx.fillStyle = gradient
        ctx.arc(particle.x, particle.y, particle.size * 2.5, 0, Math.PI * 2)
        ctx.fill()
      })
    }

    const render = (currentTime) => {
      // 帧率限制：只在达到目标帧率间隔时渲染
      if (currentTime - lastFrameTime >= FRAME_INTERVAL) {
        ctx.clearRect(0, 0, width, height)
        ctx.globalCompositeOperation = 'lighter'
        drawParticles(floatingParticles)
        drawBurstParticles()
        lastFrameTime = currentTime
      }
      animationFrameId = requestAnimationFrame(render)
    }

    const handleClick = (event) => {
      const rect = canvas.getBoundingClientRect()
      const x = event.clientX - rect.left
      const y = event.clientY - rect.top
      const burst = Array.from({ length: 5 }, () => createBurstParticle(x, y))  // 进一步减少爆发粒子数量
      burstParticles = [...burstParticles, ...burst]
    }

    const handleResize = () => {
      ctx.setTransform(1, 0, 0, 1, 0, 0)
      setCanvasSize()
    }

    setCanvasSize()
    render()

    window.addEventListener('click', handleClick)
    window.addEventListener('resize', handleResize)

    return () => {
      cancelAnimationFrame(animationFrameId)
      window.removeEventListener('click', handleClick)
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  return <canvas ref={canvasRef} className="glitter-canvas" aria-hidden="true" />
}

export default GlitterBackground
