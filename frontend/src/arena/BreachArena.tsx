import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Stars, Text, Float } from '@react-three/drei'
import { Component, useMemo, useRef, useState, type ReactNode } from 'react'
import * as THREE from 'three'
import type { Mesh, Group } from 'three'

export type Decision = 'idle' | 'allow' | 'deny' | 'approval_required'

export type ArenaEvent = {
  target: string
  tool: string
  mode?: 'jail' | 'god'
  decision: Exclude<Decision, 'idle'>
  risk: string
  reason: string
  scars: number
  matched_scar: boolean
  executed?: boolean
  pending_id?: string | null
  transition: { status: string; summary: string }
  environment: { workloads: Record<string, string>; identities?: Record<string, string> }
  attack_variant?: string | null
  candidate_scar_index?: number | null
  attacker_proposal?: {
    source: string
    requested_tool: string
    parameters: Record<string, unknown>
    rationale: string
    model: string
    model_powered: boolean
  } | null
}

const VAULTS = {
  'GPU FLEET': new THREE.Vector3(-5.2, 0.4, 0),
  'IDENTITY VAULT': new THREE.Vector3(5.2, 0.4, 0),
} as const

function Core({ decision }: { decision: Decision }) {
  const mesh = useRef<Mesh>(null)
  const color =
    decision === 'deny' ? '#ff3d61' : decision === 'allow' ? '#61f6cd' : '#8d9dff'

  useFrame(({ clock }) => {
    if (!mesh.current) return
    const t = clock.getElapsedTime()
    mesh.current.rotation.y = t * 0.45
    mesh.current.rotation.x = Math.sin(t * 0.3) * 0.15
    const pulse = decision === 'deny' ? 0.12 : 0.06
    mesh.current.scale.setScalar(1 + Math.sin(t * 2.4) * pulse)
  })

  return (
    <Float speed={1.2} rotationIntensity={0.2} floatIntensity={0.35}>
      <mesh ref={mesh}>
        <icosahedronGeometry args={[1.2, 2]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={2.4}
          wireframe
          metalness={0.6}
          roughness={0.2}
        />
      </mesh>
      <mesh scale={1.35}>
        <icosahedronGeometry args={[1.2, 1]} />
        <meshStandardMaterial
          color={color}
          transparent
          opacity={0.08}
          emissive={color}
          emissiveIntensity={0.6}
        />
      </mesh>
      <pointLight color={color} intensity={decision === 'idle' ? 12 : 28} distance={14} />
    </Float>
  )
}

function Vault({
  label,
  position,
  active,
  scarred,
  decision,
}: {
  label: string
  position: THREE.Vector3
  active: boolean
  scarred: boolean
  decision: Decision
}) {
  const group = useRef<Group>(null)
  const accent =
    decision === 'deny' && active ? '#ff3d61' : decision === 'allow' && active ? '#61f6cd' : '#6e82c4'

  useFrame(({ clock }) => {
    if (!group.current) return
    group.current.position.y = position.y + Math.sin(clock.getElapsedTime() + position.x) * 0.08
  })

  return (
    <group ref={group} position={position}>
      <mesh>
        <boxGeometry args={[2.2, 2.6, 2.2]} />
        <meshStandardMaterial
          color="#0a1228"
          emissive={accent}
          emissiveIntensity={active ? 1.4 : 0.25}
          metalness={0.55}
          roughness={0.35}
        />
      </mesh>
      <mesh position={[0, 1.55, 0]}>
        <boxGeometry args={[2.35, 0.18, 2.35]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={active ? 2 : 0.5} />
      </mesh>
      {scarred ? (
        <mesh position={[0, 0, 1.15]}>
          <planeGeometry args={[1.6, 1.8]} />
          <meshStandardMaterial
            color="#2a0810"
            emissive="#ff3d61"
            emissiveIntensity={1.2}
            transparent
            opacity={0.85}
          />
        </mesh>
      ) : null}
      <Text position={[0, -1.7, 0]} fontSize={0.28} color="#b9c8ee" anchorX="center">
        {label}
      </Text>
    </group>
  )
}

function EnergyBeam({ target, decision }: { target: string | null; decision: Decision }) {
  const ref = useRef<Mesh>(null)
  const dest = target && target in VAULTS ? VAULTS[target as keyof typeof VAULTS] : null
  const color = decision === 'deny' ? '#ff3d61' : decision === 'allow' ? '#61f6cd' : '#8d9dff'

  const { position, quaternion, length } = useMemo(() => {
    if (!dest) {
      return {
        position: new THREE.Vector3(0, 0, 0),
        quaternion: new THREE.Quaternion(),
        length: 0.01,
      }
    }
    const start = new THREE.Vector3(0, 0.4, 0)
    const end = dest.clone()
    const dir = end.clone().sub(start)
    const len = Math.max(dir.length(), 0.01)
    const mid = start.clone().add(end).multiplyScalar(0.5)
    const quat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize())
    return { position: mid, quaternion: quat, length: len }
  }, [dest])

  useFrame(({ clock }) => {
    if (!ref.current || !dest) return
    const pulse = 0.85 + Math.sin(clock.getElapsedTime() * 8) * 0.15
    ref.current.scale.set(pulse, 1, pulse)
  })

  if (!dest) return null
  return (
    <mesh ref={ref} position={position} quaternion={quaternion}>
      <cylinderGeometry args={[0.06, 0.06, length, 16]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={3} transparent opacity={0.85} />
    </mesh>
  )
}

function ScarWall({ scars, matched }: { scars: number; matched: boolean }) {
  const panels = Math.min(Math.max(scars, 0), 6)
  return (
    <group position={[0, 0.2, -6.5]}>
      <mesh>
        <boxGeometry args={[8, 3.2, 0.25]} />
        <meshStandardMaterial color="#040816" metalness={0.7} roughness={0.4} />
      </mesh>
      <Text position={[0, 1.3, 0.2]} fontSize={0.22} color="#7890bd" anchorX="center">
        SCAR MEMORY WALL
      </Text>
      {Array.from({ length: panels }).map((_, i) => (
        <mesh key={i} position={[-2.8 + i * 1.1, 0, 0.2]}>
          <boxGeometry args={[0.9, 1.4, 0.12]} />
          <meshStandardMaterial
            color="#1a0a12"
            emissive={matched && i === panels - 1 ? '#ffd36c' : '#ff3d61'}
            emissiveIntensity={matched && i === panels - 1 ? 2.2 : 1.1}
          />
        </mesh>
      ))}
      {scars === 0 && (
        <Text position={[0, 0, 0.2]} fontSize={0.18} color="#4a5d88" anchorX="center">
          empty — no attacks confirmed
        </Text>
      )}
    </group>
  )
}

function FloorPulse({ decision }: { decision: Decision }) {
  const color = decision === 'deny' ? '#4a1020' : decision === 'allow' ? '#0a2a24' : '#0a142b'
  return (
    <>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2.1, 0]}>
        <circleGeometry args={[11, 96]} />
        <meshStandardMaterial color={color} metalness={0.5} roughness={0.8} />
      </mesh>
      <gridHelper args={[24, 24, '#1b315c', '#0a142b']} position={[0, -2.08, 0]} />
    </>
  )
}

function ArenaScene({ event }: { event: ArenaEvent | null }) {
  const decision: Decision = event?.decision ?? 'idle'
  const target = event?.target ?? null

  return (
    <>
      <color attach="background" args={['#02040c']} />
      <fog attach="fog" args={['#02040c', 18, 42]} />
      <ambientLight intensity={0.28} />
      <pointLight position={[0, 8, 2]} color="#7e8cff" intensity={20} />
      <Stars radius={60} depth={28} count={1200} factor={2.2} saturation={0} fade speed={0.4} />
      <Core decision={decision} />
      <EnergyBeam target={target} decision={decision} />
      <Vault
        label="GPU FLEET"
        position={VAULTS['GPU FLEET']}
        active={target === 'GPU FLEET'}
        scarred={false}
        decision={decision}
      />
      <Vault
        label="IDENTITY"
        position={VAULTS['IDENTITY VAULT']}
        active={target === 'IDENTITY VAULT'}
        scarred={Boolean(event && event.scars > 0 && target === 'IDENTITY VAULT')}
        decision={decision}
      />
      <ScarWall scars={event?.scars ?? 0} matched={Boolean(event?.matched_scar)} />
      <FloorPulse decision={decision} />
      <OrbitControls
        enablePan={false}
        minDistance={11}
        maxDistance={22}
        maxPolarAngle={Math.PI / 2.05}
        autoRotate={decision === 'idle'}
        autoRotateSpeed={0.35}
      />
    </>
  )
}

class ArenaErrorBoundary extends Component<
  { children: ReactNode; onReset: () => void },
  { failed: boolean }
> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch() {
    this.setState({ failed: true })
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="arena-recover">
          <p>3D context was interrupted.</p>
          <button type="button" onClick={() => { this.setState({ failed: false }); this.props.onReset() }}>
            Reload 3D arena
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

/** Full 3D Breach Arena (default). Dark clear color; remount on context loss. */
export function BreachArena({ event }: { event: ArenaEvent | null }) {
  const [canvasKey, setCanvasKey] = useState(0)

  return (
    <div className="arena-stage-root arena-stage-root--3d">
      <ArenaErrorBoundary onReset={() => setCanvasKey((k) => k + 1)}>
        <Canvas
          key={canvasKey}
          camera={{ position: [0, 7.5, 16], fov: 44 }}
          dpr={[1, 1.75]}
          gl={{ antialias: true, alpha: false, powerPreference: 'high-performance' }}
          onCreated={({ gl }) => {
            gl.setClearColor('#02040c', 1)
            const el = gl.domElement
            el.addEventListener(
              'webglcontextlost',
              (e) => {
                e.preventDefault()
                setCanvasKey((k) => k + 1)
              },
              false,
            )
          }}
          style={{ width: '100%', height: '100%', display: 'block', background: '#02040c' }}
        >
          <ArenaScene event={event} />
        </Canvas>
      </ArenaErrorBoundary>
    </div>
  )
}
