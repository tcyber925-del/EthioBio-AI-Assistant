'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { motion, AnimatePresence, MotionConfig } from 'framer-motion'
import { BookOpen, Sparkles, GraduationCap } from 'lucide-react'

export default function ConsoleTabs() {
  const t = useTranslations('landing')
  const [activeTab, setActiveTab] = useState<'student' | 'teacher' | 'quiz'>('student')

  // Student Bot State
  const [selectedBotQuestion, setSelectedBotQuestion] = useState(0)

  // Teacher Workspace State
  const [gradeLevel, setGradeLevel] = useState(10)
  const [topic, setTopic] = useState('Photosynthesis')
  const [isGeneratingLesson, setIsGeneratingLesson] = useState(false)
  const [generatedLesson, setGeneratedLesson] = useState<any>(null)

  // Quiz Simulator State
  const [abilityScore, setAbilityScore] = useState(0.0) // Theta from -3.0 to +3.0
  const [quizStep, setQuizStep] = useState(0)
  const [quizHistory, setQuizHistory] = useState<Array<{ q: string, difficulty: number, correct: boolean }>>([])

  // Teacher generator simulator
  const handleGenerateLesson = () => {
    setIsGeneratingLesson(true)
    setTimeout(() => {
      setGeneratedLesson({
        title: `Lesson Plan: ${topic}`,
        objectives: [
          `Describe the light-dependent reactions of ${topic}.`,
          `Analyze the role of ATP and NADPH in the Calvin Cycle.`,
          `Explain how carbon dioxide, light intensity, and temperature affect the rate.`
        ],
        differentiation: {
          extended: 'Extended Mastery: Design an experiment to test different light wavelengths on Elodea plants.',
          structured: 'Structured Support: Guided worksheets labeling the parts of the chloroplast.'
        },
        exitTicket: 'Name the final electron acceptor in the light-dependent reactions and describe its role.'
      })
      setIsGeneratingLesson(false)
    }, 1500)
  }

  // Quiz Simulator handler
  const handleQuizAnswer = (correct: boolean) => {
    const currentQ = quizQuestions[quizStep % quizQuestions.length]
    // Bayesian ability updates (simplified IRT model):
    // Theta = Theta + learning_rate * (correct - probability_of_correct)
    // probability_of_correct = 1 / (1 + exp(-(Theta - difficulty)))
    const diff = currentQ.difficulty
    const prob = 1 / (1 + Math.exp(-(abilityScore - diff)))
    const learningRate = 0.8
    const newAbility = abilityScore + learningRate * ((correct ? 1 : 0) - prob)
    const clampedAbility = Math.max(-3.0, Math.min(3.0, newAbility))

    setAbilityScore(Number(clampedAbility.toFixed(2)))
    setQuizHistory(prev => [...prev, { q: currentQ.question, difficulty: diff, correct }])
    setQuizStep(prev => prev + 1)
  }

  const resetQuizSimulator = () => {
    setAbilityScore(0.0)
    setQuizStep(0)
    setQuizHistory([])
  }

  const botFlows = [
    {
      q: "What is the difference between prokaryotic and eukaryotic cells?",
      a: "Prokaryotic cells (e.g., bacteria) lack a membrane-bound nucleus and organelles, carrying circular DNA in a nucleoid region. Eukaryotic cells (e.g., plant/animal cells) have a true nucleus enclosing linear chromosomes and membrane-bound organelles.",
      source: "Grade 9 Biology Textbook",
      unit: "Unit 2: Cell Biology",
      page: "Page 34"
    },
    {
      q: "Balance the reaction: hydrogen gas burns in oxygen to form water.",
      a: "The balanced equation is 2H\u2082 + O\u2082 \u2192 2H\u2082O. Four hydrogen atoms and two oxygen atoms on each side. The reaction is exothermic, releasing energy as new bonds form in water \u2014 always check that both atom counts and charge balance.",
      source: "Grade 10 Chemistry Textbook",
      unit: "Unit 3: Chemical Reactions",
      page: "Page 58"
    },
    {
      q: "A force of 12 N acts on a 3 kg block. What is its acceleration?",
      a: "Newton's second law gives a = F/m = 12 N \u00f7 3 kg = 4 m/s\u00b2. The acceleration points in the same direction as the net force, assuming no friction opposes the motion.",
      source: "Grade 11 Physics Textbook",
      unit: "Unit 2: Motion and Forces",
      page: "Page 41"
    }
  ]

  const quizQuestions = [
    { question: "Identifies the primary site of photosynthesis inside plant cells.", difficulty: -1.0, label: "Chloroplast (Basic)" },
    { question: "The SI unit of force is named after which scientist?", difficulty: 0.0, label: "Newton (Medium)" },
    { question: "How many moles of O\u2082 fully combust one mole of CH\u2084?", difficulty: 1.0, label: "Stoichiometry (Hard)" },
    { question: "The derivative of x\u00b2 with respect to x equals...", difficulty: 2.0, label: "Power Rule (Extreme)" }
  ]

  const tabs: Array<{ id: typeof activeTab; labelKey: string }> = [
    { id: 'student', labelKey: 'console_student' },
    { id: 'teacher', labelKey: 'console_teacher' },
    { id: 'quiz', labelKey: 'console_quiz' },
  ]

  return (
    <MotionConfig reducedMotion="user">
      <section id="console" className="mx-auto max-w-7xl border-b border-[#2d2d2d] px-4 py-20 sm:px-6 lg:px-8">
        <div className="mb-12 text-center">
          <h2 className="verge-display mb-4 text-3xl text-white sm:text-4xl">{t('console_title')}</h2>
          <p className="mx-auto max-w-2xl font-sans text-gray-400">{t('console_desc')}</p>
          <p className="mx-auto mt-2 font-mono text-[10px] uppercase tracking-wider text-gray-500">
            {t('demo_caption')}
          </p>
        </div>

        {/* Tab Switchers */}
        <div className="mb-8 flex flex-wrap gap-1 border-b border-[#2d2d2d] bg-[#181818] p-1">
          {tabs.map(({ id, labelKey }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex-1 min-w-[150px] border py-3 text-xs font-mono font-bold uppercase tracking-wider transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3cffd0] ${
                activeTab === id ? 'border-[#5200ff] bg-[#5200ff] text-white' : 'border-transparent text-gray-500 hover:bg-white/5 hover:text-white'
              }`}
            >
              <span className="mr-1 opacity-60">{t('demo_badge')}</span>· {t(labelKey)}
            </button>
          ))}
        </div>

        {/* Console Box Container */}
        <div className="flex min-h-[420px] flex-col justify-between border border-[#2d2d2d] bg-[#181818] p-6 md:p-8">
          <AnimatePresence mode="wait">
            {activeTab === 'student' && (
              <motion.div
                key="student"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="grid grid-cols-1 gap-8 lg:grid-cols-3"
              >
                {/* Left side query switcher */}
                <div className="space-y-3 border-r border-[#2d2d2d]/50 pr-0 flex-col justify-center lg:col-span-1 lg:pr-6 flex">
                  <span className="verge-label mb-2 block text-[#3cffd0]">Choose Sample Query</span>
                  {botFlows.map((flow, index) => (
                    <button
                      key={index}
                      onClick={() => setSelectedBotQuestion(index)}
                      className={`w-full rounded-none border p-3 text-left text-xs font-mono transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3cffd0] ${selectedBotQuestion === index ? 'border-[#3cffd0] bg-[#3cffd0]/10 text-[#3cffd0]' : 'border-[#2d2d2d] text-gray-400 hover:border-gray-500 hover:text-white'}`}
                    >
                      {flow.q}
                    </button>
                  ))}
                </div>

                {/* Right side bot screen mockup */}
                <div className="flex h-full min-h-[300px] flex-col justify-between border border-[#2d2d2d] bg-[#111] p-4 font-mono text-sm leading-relaxed text-gray-300 lg:col-span-2">
                  <div>
                    {/* Bot header bar */}
                    <div className="mb-4 flex items-center justify-between border-b border-[#2d2d2d] pb-2">
                      <div className="flex items-center space-x-2">
                        <div className="h-2.5 w-2.5 rounded-full bg-green-500"></div>
                        <span className="verge-label text-xs text-white">EthioSci Bot</span>
                      </div>
                      <span className="text-[10px] text-gray-500">Telegram Mock</span>
                    </div>

                    {/* Chat Bubble Student */}
                    <div className="mb-4 flex flex-col items-end">
                      <span className="mr-1 mb-1 text-[10px] text-gray-500">Student</span>
                      <div className="max-w-[85%] border border-[#333] bg-[#222] px-3 py-2 text-xs text-white">
                        {botFlows[selectedBotQuestion].q}
                      </div>
                    </div>

                    {/* Chat Bubble Assistant */}
                    <div className="flex flex-col items-start mb-4">
                      <span className="ml-1 mb-1 text-[10px] text-[#3cffd0]">EthioSci</span>
                      <div className="max-w-[85%] border border-[#3cffd0]/30 bg-[#1e2a27] px-3 py-2 text-xs text-[#e5fbf6]">
                        {botFlows[selectedBotQuestion].a}
                      </div>
                    </div>
                  </div>

                  {/* Sources citation block */}
                  <div className="mt-4 flex items-center justify-between border-t border-[#2d2d2d] bg-[#161616] p-2 pt-3 text-xs text-gray-400">
                    <div className="flex items-center space-x-2">
                      <BookOpen className="h-3.5 w-3.5 text-[#3cffd0]" />
                      <span>{botFlows[selectedBotQuestion].source}</span>
                    </div>
                    <div className="flex space-x-2 font-bold text-white">
                      <span className="border border-[#5200ff]/30 bg-[#5200ff]/20 px-1.5 py-0.5 font-mono text-[10px] uppercase">{botFlows[selectedBotQuestion].unit}</span>
                      <span className="bg-[#3cffd0]/20 px-1.5 py-0.5 font-mono text-[10px] text-[#3cffd0]">{botFlows[selectedBotQuestion].page}</span>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'teacher' && (
              <motion.div
                key="teacher"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="grid grid-cols-1 gap-8 lg:grid-cols-3"
              >
                {/* Left Form */}
                <div className="flex flex-col justify-center space-y-4 border-r border-[#2d2d2d]/50 pr-0 lg:col-span-1 lg:pr-6">
                  <div>
                    <label className="verge-label mb-2 block text-[#3cffd0]">Grade Level</label>
                    <select
                      value={gradeLevel}
                      onChange={(e) => setGradeLevel(Number(e.target.value))}
                      className="w-full rounded-none border border-[#2d2d2d] bg-[#111] p-2 font-mono text-xs text-white outline-none focus:border-[#3cffd0]"
                    >
                      <option value={9}>Grade 9</option>
                      <option value={10}>Grade 10</option>
                      <option value={11}>Grade 11</option>
                      <option value={12}>Grade 12</option>
                    </select>
                  </div>
                  <div>
                    <label className="verge-label mb-2 block text-[#3cffd0]">Topic</label>
                    <input
                      type="text"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      className="w-full rounded-none border border-[#2d2d2d] bg-[#111] p-2 font-mono text-xs text-white outline-none focus:border-[#3cffd0]"
                    />
                  </div>
                  <button
                    onClick={handleGenerateLesson}
                    disabled={isGeneratingLesson}
                    className="flex w-full items-center justify-center space-x-2 rounded-none border border-black bg-[#3cffd0] py-3 font-mono text-xs font-bold uppercase tracking-wider text-black transition-all hover:bg-[#2be0b5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3cffd0]"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>{isGeneratingLesson ? "Generating Plan..." : "Generate Lesson Plan"}</span>
                  </button>
                </div>

                {/* Right Mock Output */}
                <div className="flex min-h-[300px] flex-col justify-between border border-[#2d2d2d] bg-[#111] p-5 font-mono text-xs text-gray-300 lg:col-span-2">
                  {isGeneratingLesson ? (
                    <div className="flex flex-grow flex-col items-center justify-center py-12">
                      <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-[#3cffd0] border-t-transparent"></div>
                      <span className="verge-label text-gray-400">Consulting Curriculum Context Graph...</span>
                    </div>
                  ) : generatedLesson ? (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between border-b border-[#2d2d2d] pb-2">
                        <span className="verge-label text-sm text-[#3cffd0]">{generatedLesson.title}</span>
                        <span className="border border-[#333] bg-[#222] px-1.5 py-0.5 text-[10px] text-gray-500">Grade {gradeLevel}</span>
                      </div>

                      <div>
                        <span className="verge-label mb-1 block text-white">Learning Objectives</span>
                        <ul className="list-disc space-y-1 pl-4 text-[11px] text-gray-400">
                          {generatedLesson.objectives.map((obj: string, i: number) => <li key={i}>{obj}</li>)}
                        </ul>
                      </div>

                      <div className="grid grid-cols-1 gap-4 border-y border-[#2d2d2d] py-3 md:grid-cols-2">
                        <div>
                          <span className="verge-label mb-1 block text-white">Extended Mastery Track</span>
                          <p className="text-[11px] leading-relaxed text-gray-400">{generatedLesson.differentiation.extended}</p>
                        </div>
                        <div>
                          <span className="verge-label mb-1 block text-white">Structured Support Track</span>
                          <p className="text-[11px] leading-relaxed text-gray-400">{generatedLesson.differentiation.structured}</p>
                        </div>
                      </div>

                      <div>
                        <span className="verge-label mb-1 block text-white">Target exit ticket question</span>
                        <p className="border border-[#2d2d2d] bg-[#161616] p-2 text-[11px] italic text-gray-400">{generatedLesson.exitTicket}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-grow flex-col items-center justify-center py-12 text-center">
                      <GraduationCap className="mb-3 h-12 w-12 animate-bounce text-[#2d2d2d]" />
                      <span className="verge-label mb-1 block text-gray-500">{t('teacher_preview_title')}</span>
                      <span className="max-w-sm text-[10px] text-gray-600">{t('teacher_preview_desc')}</span>
                    </div>
                  )}

                  <div className="mt-4 flex items-center justify-between border-t border-[#2d2d2d]/50 pt-2 text-[10px] text-gray-500">
                    <span>Generated in markdown format</span>
                    <span className="text-[#3cffd0]">● Ready for exports (Word/PDF)</span>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'quiz' && (
              <motion.div
                key="quiz"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="grid grid-cols-1 gap-8 lg:grid-cols-3"
              >
                {/* Left Controller */}
                <div className="flex flex-col justify-center space-y-4 border-r border-[#2d2d2d]/50 pr-0 lg:col-span-1 lg:pr-6">
                  <div className="border border-[#2d2d2d] bg-[#111] p-4 text-center">
                    <span className="verge-label mb-1 block text-white">Ability Estimate (θ)</span>
                    <span className={`verge-display block text-4xl font-black ${abilityScore >= 1.0 ? 'text-green-400' : abilityScore <= -1.0 ? 'text-red-400' : 'text-[#3cffd0]'}`}>
                      {abilityScore > 0 ? `+${abilityScore}` : abilityScore}
                    </span>
                    <span className="font-mono text-[10px] text-gray-500">Calibrated Range: -3.0 to +3.0</span>

                    {/* Proficiency Band Bar */}
                    <div className="mt-4 h-2.5 w-full overflow-hidden rounded-full border border-[#333] bg-[#222]">
                      <div
                        className={`h-full transition-all duration-300 ${abilityScore >= 1.0 ? 'bg-green-400' : abilityScore <= -1.0 ? 'bg-red-400' : 'bg-[#3cffd0]'}`}
                        style={{ width: `${((abilityScore + 3) / 6) * 100}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => handleQuizAnswer(true)}
                      className="flex-1 rounded-none border border-black bg-[#3cffd0] py-3 font-mono text-xs font-bold uppercase tracking-wider text-black transition-all hover:bg-[#2be0b5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3cffd0]"
                    >
                      Answer Correct
                    </button>
                    <button
                      onClick={() => handleQuizAnswer(false)}
                      className="flex-1 rounded-none border border-red-500/50 bg-red-500/20 py-3 font-mono text-xs font-bold uppercase tracking-wider text-red-400 transition-all hover:bg-red-500/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3cffd0]"
                    >
                      Answer Wrong
                    </button>
                  </div>

                  <button
                    onClick={resetQuizSimulator}
                    className="w-full rounded-none border border-[#2d2d2d] bg-transparent py-1.5 font-mono text-[10px] uppercase text-gray-400 transition-all hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3cffd0]"
                  >
                    Reset Profiler
                  </button>
                </div>

                {/* Right Status Chart */}
                <div className="flex min-h-[300px] flex-col justify-between border border-[#2d2d2d] bg-[#111] p-5 font-mono text-xs text-gray-300 lg:col-span-2">
                  <div>
                    <div className="mb-4 flex items-center justify-between border-b border-[#2d2d2d] pb-2">
                      <span className="verge-label text-[#3cffd0]">{t('quiz_preview_title')}</span>
                      <span className="border border-[#333] bg-[#222] px-1.5 py-0.5 text-[10px] text-gray-500">Adaptive Assessment Mode</span>
                    </div>

                    <div className="space-y-3">
                      <div>
                        <span className="verge-label mb-1 block text-gray-500">Current Calibrated Question Target</span>
                        <div className="border border-[#2d2d2d] bg-[#181818] p-3 text-white">
                          <div className="mb-1.5 flex items-center justify-between">
                            <span className="text-[10px] font-bold uppercase text-[#3cffd0]">Difficulty: {quizQuestions[quizStep % quizQuestions.length].difficulty}</span>
                            <span className="text-[10px] text-gray-500">{quizQuestions[quizStep % quizQuestions.length].label}</span>
                          </div>
                          <p className="text-xs text-gray-300">{quizQuestions[quizStep % quizQuestions.length].question}</p>
                        </div>
                      </div>

                      {/* History Log */}
                      {quizHistory.length > 0 && (
                        <div>
                          <span className="verge-label mb-1 block text-gray-500">Recalibration History</span>
                          <div className="max-h-[100px] space-y-1.5 overflow-y-auto pr-2">
                            {quizHistory.map((item, i) => (
                              <div key={i} className="flex items-center justify-between border border-[#2d2d2d] bg-[#161616] p-1.5 text-[10px]">
                                <span className="max-w-[70%] truncate">{item.q}</span>
                                <div className="flex space-x-2">
                                  <span className="text-gray-500">Diff: {item.difficulty}</span>
                                  <span className={item.correct ? "text-green-400" : "text-red-400"}>
                                    {item.correct ? "✓ Correct" : "✗ Incorrect"}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 border-t border-[#2d2d2d]/50 pt-2 text-center text-[10px] text-gray-500">
                    {t('quiz_preview_desc')}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </section>
    </MotionConfig>
  )
}