"use client"

import { useState } from "react"
import { Brain } from "lucide-react"
import { DashboardLayout } from "@/components/dashboard-v2/DashboardLayout"
import { MisconceptionHeatmap } from "@/components/misconceptions/MisconceptionHeatmap"
import { MisconceptionPanel } from "@/components/misconceptions/MisconceptionPanel"

export default function MisconceptionsPage() {
  const [userId, setUserId] = useState("")
  const [classroomId, setClassroomId] = useState("")
  const [view, setView] = useState<"classroom" | "student">("classroom")

  return (
    <DashboardLayout breadcrumbs={[{ label: "Misconceptions" }]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-v2-foreground">Misconception Intelligence</h1>
          <p className="text-sm text-v2-muted-foreground mt-1">
            Detect, track, and remediate student misconceptions across topics and classrooms
          </p>
        </div>

        <div className="flex items-center gap-2 bg-v2-card rounded-lg border border-v2-border p-1 w-fit">
          <button
            onClick={() => setView("classroom")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              view === "classroom"
                ? "bg-v2-accent text-white"
                : "text-v2-muted-foreground hover:text-v2-foreground"
            }`}
          >
            Classroom View
          </button>
          <button
            onClick={() => setView("student")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              view === "student"
                ? "bg-v2-accent text-white"
                : "text-v2-muted-foreground hover:text-v2-foreground"
            }`}
          >
            Student View
          </button>
        </div>

        {view === "classroom" ? (
          <div className="space-y-4">
            <input
              type="text"
              placeholder="Enter classroom ID..."
              value={classroomId}
              onChange={(e) => setClassroomId(e.target.value)}
              className="w-full max-w-xs px-3 py-2 text-sm bg-v2-card border border-v2-border rounded-lg focus:outline-none focus:ring-2 focus:ring-v2-accent/50 text-v2-foreground placeholder:text-v2-muted-foreground"
            />
            {classroomId ? (
              <MisconceptionHeatmap classroomId={classroomId} />
            ) : (
              <div className="flex flex-col items-center gap-3 py-16 text-v2-muted-foreground">
                <Brain size={40} className="opacity-40" />
                <p className="text-sm">Enter a classroom ID to view the misconception heatmap</p>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <input
              type="text"
              placeholder="Enter student UUID..."
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className="w-full max-w-xs px-3 py-2 text-sm bg-v2-card border border-v2-border rounded-lg focus:outline-none focus:ring-2 focus:ring-v2-accent/50 text-v2-foreground placeholder:text-v2-muted-foreground"
            />
            {userId ? (
              <MisconceptionPanel userId={userId} />
            ) : (
              <div className="flex flex-col items-center gap-3 py-16 text-v2-muted-foreground">
                <Brain size={40} className="opacity-40" />
                <p className="text-sm">Enter a student UUID to view their misconception profile</p>
              </div>
            )}
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
