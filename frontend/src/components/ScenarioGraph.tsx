import { useEffect, useRef } from 'react'
import cytoscape from 'cytoscape'
import type { MapEntity, MapLink } from './SimulationMap'

const TYPE_COLORS: Record<string, string> = {
  missile: '#ef4444', radar: '#3b82f6', interceptor: '#22c55e',
  弹道导弹: '#ef4444', 雷达站: '#3b82f6', 拦截弹: '#22c55e',
}

function getColor(name: string): string {
  if (name.includes('导弹') || name.includes('26B')) return TYPE_COLORS.missile
  if (name.includes('雷达')) return TYPE_COLORS.radar
  if (name.includes('红旗') || name.includes('拦截')) return TYPE_COLORS.interceptor
  return '#6b7280'
}

function getNodeLabel(name: string): string {
  return name.length > 6 ? name.slice(0, 6) + '…' : name
}

export default function ScenarioGraph({
  entities, links, height = 240,
}: {
  entities: MapEntity[]
  links: MapLink[]
  height?: number
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const initializedRef = useRef(false)
  const prevEntitiesRef = useRef<MapEntity[]>([])
  const isFirstLayoutRef = useRef(true)

  useEffect(() => {
    if (!containerRef.current) return
    const cy = cyRef.current
    if (!cy) return

    const prevIds = new Set(prevEntitiesRef.current.map(e => e.id))
    const currIds = new Set(entities.map(e => e.id))
    const hasNewNodes = [...currIds].some(id => !prevIds.has(id))
    const hasRemovedNodes = [...prevIds].some(id => !currIds.has(id))

    cy.batch(() => {
      // Remove stale nodes and edges
      cy.nodes().forEach(n => {
        if (!currIds.has(n.id())) {
          cy.remove(n)
        }
      })

      // Add/update nodes
      entities.forEach(e => {
        const existing = cy.getElementById(e.id)
        if (existing.length === 0) {
          cy.add({
            data: {
              id: e.id,
              label: getNodeLabel(e.name),
              color: getColor(e.name),
            }
          })
        } else {
          existing.data('label', getNodeLabel(e.name))
          const newColor = getColor(e.name)
          if (existing.data('color') !== newColor) {
            existing.data('color', newColor)
            existing.style('background-color', newColor)
            existing.style('text-outline-color', newColor)
          }
        }
      })

      // Build desired edges
      const entityNameMap = new Map(entities.map(e => [e.name, e]))
      const desiredEdgeMap = new Map<string, { data: Record<string, string> }>()

      links.forEach(l => {
        const srcEnt = entityNameMap.get(l.sourceName)
        const tgtEnt = entityNameMap.get(l.targetName)
        if (!srcEnt || !tgtEnt) return
        const key = `${srcEnt.id}|${tgtEnt.id}|${l.linkTypeId || ''}`
        desiredEdgeMap.set(key, {
          data: {
            id: key,
            source: srcEnt.id,
            target: tgtEnt.id,
            label: (l.linkTypeId || '').includes('detect') || (l.linkTypeId || '').includes('探测')
              ? '探测' : (l.linkTypeId || '').includes('intercept') || (l.linkTypeId || '').includes('拦截')
              ? '拦截' : (l.linkTypeId || '').slice(0, 4),
            edgeColor: (l.linkTypeId || '').includes('intercept') || (l.linkTypeId || '').includes('拦截')
              ? '#ef4444' : '#3b82f6',
          }
        })
      })

      // Remove stale edges
      cy.edges().forEach(e => {
        if (!desiredEdgeMap.has(e.id())) {
          cy.remove(e)
        }
      })

      // Add new edges
      desiredEdgeMap.forEach((edgeData, key) => {
        if (cy.getElementById(key).length === 0) {
          const srcNode = cy.getElementById(edgeData.data.source)
          const tgtNode = cy.getElementById(edgeData.data.target)
          if (srcNode.length > 0 && tgtNode.length > 0) {
            cy.add(edgeData)
          }
        }
      })
    })

    // Run layout only when structure changes (nodes added/removed)
    if (entities.length > 0 && (isFirstLayoutRef.current || hasNewNodes || hasRemovedNodes)) {
      const opts = {
        name: 'cose',
        animate: false,
        fit: isFirstLayoutRef.current,
        padding: 30,
        randomize: isFirstLayoutRef.current,
        nodeRepulsion: () => 10000,
        nodeOverlap: 40,
        idealEdgeLength: () => 150,
        edgeElasticity: () => 80,
        gravity: 0.8,
        numIter: isFirstLayoutRef.current ? 300 : 200,
        initialTemp: 150,
        coolingFactor: 0.9,
        minTemp: 1.0,
        nodeDimensionsIncludeLabels: true,
      } as any
      const layout = cy.layout(opts)
      if (isFirstLayoutRef.current) {
        layout.run()
        isFirstLayoutRef.current = false
      } else {
        layout.one('layoutstop', () => {
          cy.fit(undefined, 30)
        })
        layout.run()
      }
    }

    prevEntitiesRef.current = entities
  }, [entities, links])

  // One-time init
  useEffect(() => {
    if (!containerRef.current || initializedRef.current) return
    const cy = cytoscape({
      container: containerRef.current,
      elements: [],
      layout: { name: 'preset' },
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'background-color': 'data(color)',
            color: '#fff',
            'font-size': '9px',
            'font-weight': 'bold',
            'text-valign': 'center',
            'text-halign': 'center',
            width: 40,
            height: 40,
            'text-outline-width': 1.5,
            'text-outline-color': 'data(color)',
          }
        },
        {
          selector: 'edge',
          style: {
            label: 'data(label)',
            'font-size': '8px',
            color: '#374151',
            'line-color': 'data(edgeColor)',
            'target-arrow-color': 'data(edgeColor)',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'text-background-color': '#ffffff',
            'text-background-opacity': 0.9,
            'text-background-padding': '1px',
            width: 1.5,
          }
        },
      ],
    })
    cyRef.current = cy
    initializedRef.current = true

    return () => {
      cy.destroy()
      cyRef.current = null
      initializedRef.current = false
    }
  }, [])

  return (
    <div className="border rounded-lg overflow-hidden bg-white flex flex-col" style={{ height }}>
      <div className="flex items-center gap-1 px-2 py-1 border-b bg-gray-50 flex-shrink-0">
        <span className="text-[10px] font-semibold text-gray-500">场景图谱</span>
        <span className="text-[10px] text-gray-400 ml-auto">{entities.length}节点 {links.length}边</span>
      </div>
      <div ref={containerRef} className="flex-1" />
    </div>
  )
}
