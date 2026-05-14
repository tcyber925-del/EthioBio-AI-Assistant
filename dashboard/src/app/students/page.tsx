'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Users, Search } from 'lucide-react'

export default function StudentsPage() {
  const [search, setSearch] = useState('')

  const students = [
    { id: '1', name: 'Grade 9 Students', count: 0, avgScore: null },
    { id: '2', name: 'Grade 10 Students', count: 0, avgScore: null },
    { id: '3', name: 'Grade 11 Students', count: 0, avgScore: null },
    { id: '4', name: 'Grade 12 Students', count: 0, avgScore: null },
  ]

  const filtered = students.filter(s =>
    s.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Students</h1>
          <p className="text-sm text-gray-500 mt-1">Track student progress and performance</p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search students..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 border rounded-lg text-sm w-64"
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border">
          <Users className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No students found</p>
          <p className="text-sm text-gray-400 mt-1">Students will appear after they interact with the bot</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filtered.map(s => (
            <Link key={s.id} href={`/students/${s.id}`}
              className="bg-white rounded-xl shadow-sm border p-5 hover:shadow-md transition-shadow flex items-center gap-4"
            >
              <div className="p-3 rounded-lg bg-purple-50 text-purple-600">
                <Users className="w-6 h-6" />
              </div>
              <div>
                <p className="font-semibold text-gray-900">{s.name}</p>
                <p className="text-sm text-gray-500">
                  {s.count} quizzes taken
                  {s.avgScore !== null ? ` · Avg: ${s.avgScore}%` : ' · No data yet'}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
