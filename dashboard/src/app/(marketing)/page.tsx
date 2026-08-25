'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Zap, 
  BookOpen, 
  Users, 
  MessageSquare, 
  ArrowRight, 
  Play, 
  Award, 
  CheckCircle,
  TrendingUp,
  LineChart,
  Brain,
  GraduationCap,
  Sparkles,
  Code,
  BarChart3
} from 'lucide-react'
import Link from 'next/link'
import { fetchWithTimeout } from '@/lib/fetch'

interface Stats {
  active_students: number
  quizzes_completed: number
  lesson_plans_generated: number
  knowledge_assets: number
  system_status: string
}

const defaultStats: Stats = {
  active_students: 1520,
  quizzes_completed: 8520,
  lesson_plans_generated: 240,
  knowledge_assets: 128,
  system_status: 'healthy'
}

export default function LandingPage() {
  const t = useTranslations('landing')
  const [stats, setStats] = useState<Stats>(defaultStats)
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

  useEffect(() => {
    // Fetch stats
    fetchWithTimeout('/auth/public-stats')
      .then((data) => {
        if (data && data.active_students) setStats(data)
      })
      .catch((err) => console.log('Stats fetch error: using static fallbacks', err))
  }, [])

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
      q: "Explain the main stages of cellular respiration.",
      a: "Cellular respiration occurs in 3 main pathways: 1. Glycolysis (in cytosol, anaerobic, breaks glucose into pyruvate), 2. Krebs Cycle (in mitochondrial matrix, generates NADH/FADH2), and 3. Electron Transport Chain (on inner mitochondrial membrane, generates ~32 ATP).",
      source: "Grade 11 Biology Textbook",
      unit: "Unit 3: Cellular Energetics",
      page: "Page 112"
    },
    {
      q: "How does natural selection drive biological evolution?",
      a: "Natural selection acts on phenotypic variations. Organisms with traits better suited to their environment have higher survival and reproductive rates, passing those advantageous alleles to offspring, increasing allele frequency over generations.",
      source: "Grade 12 Biology Textbook",
      unit: "Unit 4: Evolution",
      page: "Page 87"
    }
  ]

  const quizQuestions = [
    { question: "Identifies the primary site of photosynthesis inside plant cells.", difficulty: -1.0, label: "Chloroplast (Basic)" },
    { question: "Splitting of water molecules during light reaction is known as...", difficulty: 0.0, label: "Photolysis (Medium)" },
    { question: "Calculates total net ATP produced by anaerobic fermentation of 1 glucose molecule.", difficulty: 1.0, label: "Anaerobic Yield (Hard)" },
    { question: "The enzyme Rubisco is responsible for catalyzing which specific step?", difficulty: 2.0, label: "Carbon Fixation (Extreme)" }
  ]

  return (
    <div className="min-h-screen bg-[#131313]">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-24 border-b border-[#2d2d2d] bg-gradient-to-b from-[#181818] to-[#131313]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
          <motion.span 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="verge-label inline-block text-[#3cffd0] bg-[#3cffd0]/10 border border-[#3cffd0]/30 px-3 py-1 rounded-sm mb-6"
          >
            {t('hero_kicker')}
          </motion.span>
          
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="verge-display text-4xl sm:text-6xl md:text-7xl font-extrabold text-white tracking-tighter leading-none mb-6 max-w-5xl mx-auto"
          >
            {t('hero_title')}
          </motion.h1>

          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="text-gray-400 text-lg sm:text-xl max-w-3xl mx-auto mb-10 leading-relaxed font-sans"
          >
            {t('hero_subtitle')}
          </motion.p>

          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Link 
              href="/login" 
              className="w-full sm:w-auto px-8 py-4 bg-[#3cffd0] hover:bg-[#2be0b5] text-black font-mono font-bold text-sm uppercase tracking-wider rounded-none border border-black hover:translate-x-[-3px] hover:translate-y-[-3px] transition-all hover:shadow-[4px_4px_0px_0px_#5200ff] text-center"
            >
              {t('cta_app')}
            </Link>
            <a 
              href="https://t.me/ethiobio_bot" 
              target="_blank" 
              rel="noopener noreferrer" 
              className="w-full sm:w-auto px-8 py-4 bg-transparent hover:bg-white/5 text-white font-mono font-bold text-sm uppercase tracking-wider rounded-none border border-gray-600 hover:border-white transition-all text-center flex items-center justify-center space-x-2"
            >
              <MessageSquare className="w-4 h-4 text-[#3cffd0]" />
              <span>{t('cta_telegram')}</span>
            </a>
          </motion.div>
        </div>

        {/* Decorative Grid Lines */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1b1b1b_1px,transparent_1px),linear-gradient(to_bottom,#1b1b1b_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] pointer-events-none z-0" />
      </section>

      {/* Interactive Features Console Section */}
      <section id="console" className="py-20 border-b border-[#2d2d2d] max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="verge-display text-3xl sm:text-4xl text-white mb-4">{t('console_title')}</h2>
          <p className="text-gray-400 max-w-2xl mx-auto font-sans">{t('console_desc')}</p>
        </div>

        {/* Tab Switchers */}
        <div className="flex flex-wrap border-b border-[#2d2d2d] mb-8 bg-[#181818] p-1 gap-1">
          <button 
            onClick={() => setActiveTab('student')}
            className={`flex-1 min-w-[150px] py-3 text-xs font-mono font-bold uppercase tracking-wider transition-all border ${activeTab === 'student' ? 'bg-[#5200ff] border-[#5200ff] text-white' : 'border-transparent text-gray-500 hover:text-white hover:bg-white/5'}`}
          >
            {t('console_student')}
          </button>
          <button 
            onClick={() => setActiveTab('teacher')}
            className={`flex-1 min-w-[150px] py-3 text-xs font-mono font-bold uppercase tracking-wider transition-all border ${activeTab === 'teacher' ? 'bg-[#5200ff] border-[#5200ff] text-white' : 'border-transparent text-gray-500 hover:text-white hover:bg-white/5'}`}
          >
            {t('console_teacher')}
          </button>
          <button 
            onClick={() => setActiveTab('quiz')}
            className={`flex-1 min-w-[150px] py-3 text-xs font-mono font-bold uppercase tracking-wider transition-all border ${activeTab === 'quiz' ? 'bg-[#5200ff] border-[#5200ff] text-white' : 'border-transparent text-gray-500 hover:text-white hover:bg-white/5'}`}
          >
            {t('console_quiz')}
          </button>
        </div>

        {/* Console Box Container */}
        <div className="bg-[#181818] border border-[#2d2d2d] rounded-none p-6 md:p-8 min-h-[420px] flex flex-col justify-between">
          <AnimatePresence mode="wait">
            {activeTab === 'student' && (
              <motion.div 
                key="student"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="grid grid-cols-1 lg:grid-cols-3 gap-8"
              >
                {/* Left side query switcher */}
                <div className="space-y-3 lg:col-span-1 border-r border-[#2d2d2d]/50 pr-0 lg:pr-6 flex flex-col justify-center">
                  <span className="verge-label text-[#3cffd0] mb-2 block">Choose Sample Query</span>
                  {botFlows.map((flow, index) => (
                    <button
                      key={index}
                      onClick={() => setSelectedBotQuestion(index)}
                      className={`w-full text-left p-3 text-xs font-mono border rounded-none transition-all ${selectedBotQuestion === index ? 'bg-[#3cffd0]/10 border-[#3cffd0] text-[#3cffd0]' : 'border-[#2d2d2d] text-gray-400 hover:border-gray-500 hover:text-white'}`}
                    >
                      {flow.q}
                    </button>
                  ))}
                </div>

                {/* Right side bot screen mockup */}
                <div className="lg:col-span-2 flex flex-col justify-between h-full bg-[#111] border border-[#2d2d2d] p-4 font-mono text-sm leading-relaxed text-gray-300 min-h-[300px]">
                  <div>
                    {/* Bot header bar */}
                    <div className="flex items-center justify-between border-b border-[#2d2d2d] pb-2 mb-4">
                      <div className="flex items-center space-x-2">
                        <div className="w-2.5 h-2.5 rounded-full bg-green-500"></div>
                        <span className="verge-label text-xs text-white">EthioSci Assistant Bot</span>
                      </div>
                      <span className="text-[10px] text-gray-500">Telegram Mock</span>
                    </div>

                    {/* Chat Bubble Student */}
                    <div className="flex flex-col items-end mb-4">
                      <span className="text-[10px] text-gray-500 mr-1 mb-1">Student</span>
                      <div className="bg-[#222] border border-[#333] px-3 py-2 text-white max-w-[85%] text-xs">
                        {botFlows[selectedBotQuestion].q}
                      </div>
                    </div>

                    {/* Chat Bubble Assistant */}
                    <div className="flex flex-col items-start mb-4">
                      <span className="text-[10px] text-[#3cffd0] ml-1 mb-1">EthioSci AI</span>
                      <div className="bg-[#1e2a27] border border-[#3cffd0]/30 px-3 py-2 text-[#e5fbf6] max-w-[85%] text-xs">
                        {botFlows[selectedBotQuestion].a}
                      </div>
                    </div>
                  </div>

                  {/* Sources citation block */}
                  <div className="border-t border-[#2d2d2d] pt-3 mt-4 flex items-center justify-between text-xs text-gray-400 bg-[#161616] p-2">
                    <div className="flex items-center space-x-2">
                      <BookOpen className="w-3.5 h-3.5 text-[#3cffd0]" />
                      <span>{botFlows[selectedBotQuestion].source}</span>
                    </div>
                    <div className="flex space-x-2 font-bold text-white">
                      <span className="bg-[#5200ff]/20 px-1.5 py-0.5 border border-[#5200ff]/30 text-[10px] uppercase font-mono">{botFlows[selectedBotQuestion].unit}</span>
                      <span className="bg-[#3cffd0]/20 px-1.5 py-0.5 border border-[#3cffd0]/30 text-[10px] text-[#3cffd0] font-mono">{botFlows[selectedBotQuestion].page}</span>
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
                className="grid grid-cols-1 lg:grid-cols-3 gap-8"
              >
                {/* Left Form */}
                <div className="space-y-4 lg:col-span-1 border-r border-[#2d2d2d]/50 pr-0 lg:pr-6 flex flex-col justify-center">
                  <div>
                    <label className="verge-label text-[#3cffd0] block mb-2">Grade Level</label>
                    <select 
                      value={gradeLevel} 
                      onChange={(e) => setGradeLevel(Number(e.target.value))}
                      className="w-full bg-[#111] border border-[#2d2d2d] text-white p-2 rounded-none font-mono text-xs focus:border-[#3cffd0] outline-none"
                    >
                      <option value={9}>Grade 9</option>
                      <option value={10}>Grade 10</option>
                      <option value={11}>Grade 11</option>
                      <option value={12}>Grade 12</option>
                    </select>
                  </div>
                  <div>
                    <label className="verge-label text-[#3cffd0] block mb-2">Topic</label>
                    <input 
                      type="text" 
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      className="w-full bg-[#111] border border-[#2d2d2d] text-white p-2 rounded-none font-mono text-xs focus:border-[#3cffd0] outline-none"
                    />
                  </div>
                  <button
                    onClick={handleGenerateLesson}
                    disabled={isGeneratingLesson}
                    className="w-full py-3 bg-[#3cffd0] hover:bg-[#2be0b5] text-black font-mono font-bold text-xs uppercase tracking-wider rounded-none border border-black transition-all flex items-center justify-center space-x-2"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{isGeneratingLesson ? "Generating Plan..." : "Generate Lesson Plan"}</span>
                  </button>
                </div>

                {/* Right Mock Output */}
                <div className="lg:col-span-2 bg-[#111] border border-[#2d2d2d] p-5 font-mono text-xs text-gray-300 min-h-[300px] flex flex-col justify-between">
                  {isGeneratingLesson ? (
                    <div className="flex flex-col items-center justify-center flex-grow py-12">
                      <div className="w-8 h-8 border-2 border-[#3cffd0] border-t-transparent rounded-full animate-spin mb-4"></div>
                      <span className="verge-label text-gray-400">Consulting Curriculum Context Graph...</span>
                    </div>
                  ) : generatedLesson ? (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between border-b border-[#2d2d2d] pb-2">
                        <span className="verge-label text-[#3cffd0] text-sm">{generatedLesson.title}</span>
                        <span className="text-[10px] text-gray-500 bg-[#222] border border-[#333] px-1.5 py-0.5">Grade {gradeLevel}</span>
                      </div>
                      
                      <div>
                        <span className="verge-label text-white block mb-1">Learning Objectives</span>
                        <ul className="list-disc pl-4 space-y-1 text-gray-400 text-[11px]">
                          {generatedLesson.objectives.map((obj: string, i: number) => <li key={i}>{obj}</li>)}
                        </ul>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-b border-[#2d2d2d] py-3">
                        <div>
                          <span className="verge-label text-white block mb-1">Extended Mastery Track</span>
                          <p className="text-gray-400 text-[11px] leading-relaxed">{generatedLesson.differentiation.extended}</p>
                        </div>
                        <div>
                          <span className="verge-label text-white block mb-1">Structured Support Track</span>
                          <p className="text-gray-400 text-[11px] leading-relaxed">{generatedLesson.differentiation.structured}</p>
                        </div>
                      </div>

                      <div>
                        <span className="verge-label text-white block mb-1">Target exit ticket question</span>
                        <p className="text-gray-400 text-[11px] bg-[#161616] p-2 border border-[#2d2d2d] italic">{generatedLesson.exitTicket}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center flex-grow py-12 text-center">
                      <GraduationCap className="w-12 h-12 text-[#2d2d2d] mb-3 animate-bounce" />
                      <span className="verge-label text-gray-500 block mb-1">{t('teacher_preview_title')}</span>
                      <span className="text-gray-600 text-[10px] max-w-sm">{t('teacher_preview_desc')}</span>
                    </div>
                  )}

                  <div className="text-[10px] text-gray-500 border-t border-[#2d2d2d]/50 pt-2 mt-4 flex justify-between items-center">
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
                className="grid grid-cols-1 lg:grid-cols-3 gap-8"
              >
                {/* Left Controller */}
                <div className="space-y-4 lg:col-span-1 border-r border-[#2d2d2d]/50 pr-0 lg:pr-6 flex flex-col justify-center">
                  <div className="bg-[#111] border border-[#2d2d2d] p-4 text-center">
                    <span className="verge-label text-white block mb-1">Ability Estimate (θ)</span>
                    <span className={`verge-display text-4xl block font-black ${abilityScore >= 1.0 ? 'text-green-400' : abilityScore <= -1.0 ? 'text-red-400' : 'text-[#3cffd0]'}`}>
                      {abilityScore > 0 ? `+${abilityScore}` : abilityScore}
                    </span>
                    <span className="text-[10px] text-gray-500 font-mono">Calibrated Range: -3.0 to +3.0</span>
                    
                    {/* Proficiency Band Bar */}
                    <div className="w-full bg-[#222] h-2.5 rounded-full mt-4 overflow-hidden border border-[#333]">
                      <div 
                        className={`h-full transition-all duration-300 ${abilityScore >= 1.0 ? 'bg-green-400' : abilityScore <= -1.0 ? 'bg-red-400' : 'bg-[#3cffd0]'}`}
                        style={{ width: `${((abilityScore + 3) / 6) * 100}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => handleQuizAnswer(true)}
                      className="flex-1 py-3 bg-[#3cffd0] hover:bg-[#2be0b5] text-black font-mono font-bold text-xs uppercase tracking-wider rounded-none border border-black transition-all"
                    >
                      Answer Correct
                    </button>
                    <button
                      onClick={() => handleQuizAnswer(false)}
                      className="flex-1 py-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 font-mono font-bold text-xs uppercase tracking-wider rounded-none border border-red-500/50 transition-all"
                    >
                      Answer Wrong
                    </button>
                  </div>
                  
                  <button
                    onClick={resetQuizSimulator}
                    className="w-full py-1.5 bg-transparent hover:bg-white/5 text-gray-400 hover:text-white font-mono text-[10px] uppercase rounded-none border border-[#2d2d2d] transition-all"
                  >
                    Reset Profiler
                  </button>
                </div>

                {/* Right Status Chart */}
                <div className="lg:col-span-2 bg-[#111] border border-[#2d2d2d] p-5 font-mono text-xs text-gray-300 min-h-[300px] flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between border-b border-[#2d2d2d] pb-2 mb-4">
                      <span className="verge-label text-[#3cffd0]">{t('quiz_preview_title')}</span>
                      <span className="text-[10px] text-gray-500 bg-[#222] px-1.5 py-0.5 border border-[#333]">Adaptive Assessment Mode</span>
                    </div>

                    <div className="space-y-3">
                      <div>
                        <span className="verge-label text-gray-500 block mb-1">Current Calibrated Question Target</span>
                        <div className="bg-[#181818] p-3 border border-[#2d2d2d] text-white">
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-[10px] text-[#3cffd0] uppercase font-bold">Difficulty: {quizQuestions[quizStep % quizQuestions.length].difficulty}</span>
                            <span className="text-[10px] text-gray-500">{quizQuestions[quizStep % quizQuestions.length].label}</span>
                          </div>
                          <p className="text-xs text-gray-300">{quizQuestions[quizStep % quizQuestions.length].question}</p>
                        </div>
                      </div>

                      {/* History Log */}
                      {quizHistory.length > 0 && (
                        <div>
                          <span className="verge-label text-gray-500 block mb-1">Recalibration History</span>
                          <div className="max-h-[100px] overflow-y-auto space-y-1.5 pr-2">
                            {quizHistory.map((item, i) => (
                              <div key={i} className="flex justify-between items-center p-1.5 border border-[#2d2d2d] bg-[#161616] text-[10px]">
                                <span className="truncate max-w-[70%]">{item.q}</span>
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

                  <div className="text-[10px] text-gray-500 border-t border-[#2d2d2d]/50 pt-2 mt-4 text-center">
                    {t('quiz_preview_desc')}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </section>

      {/* Feature Grid Highlights */}
      <section id="features" className="py-20 border-b border-[#2d2d2d] bg-[#181818]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="verge-display text-3xl sm:text-4xl text-white mb-4">{t('section_features')}</h2>
            <p className="text-gray-400 max-w-xl mx-auto font-sans">{t('features_subtitle')}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="border border-[#2d2d2d] bg-[#131313] p-6 flex flex-col justify-between hover:border-[#3cffd0] transition-colors">
              <div>
                <BookOpen className="w-8 h-8 text-[#3cffd0] mb-4" />
                <h3 className="verge-label text-base text-white mb-2">{t('feature_textbook')}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{t('feature_textbook_desc')}</p>
              </div>
              <span className="text-[10px] text-gray-600 font-mono mt-6">Citations verified</span>
            </div>

            <div className="border border-[#2d2d2d] bg-[#131313] p-6 flex flex-col justify-between hover:border-[#3cffd0] transition-colors">
              <div>
                <Brain className="w-8 h-8 text-[#3cffd0] mb-4" />
                <h3 className="verge-label text-base text-white mb-2">{t('feature_gamification')}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{t('feature_gamification_desc')}</p>
              </div>
              <span className="text-[10px] text-gray-600 font-mono mt-6">Bayesian IRT estimation</span>
            </div>

            <div className="border border-[#2d2d2d] bg-[#131313] p-6 flex flex-col justify-between hover:border-[#3cffd0] transition-colors">
              <div>
                <Zap className="w-8 h-8 text-[#3cffd0] mb-4" />
                <h3 className="verge-label text-base text-white mb-2">{t('feature_recovery')}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{t('feature_recovery_desc')}</p>
              </div>
              <span className="text-[10px] text-gray-600 font-mono mt-6">Automatic recovery</span>
            </div>

            <div className="border border-[#2d2d2d] bg-[#131313] p-6 flex flex-col justify-between hover:border-[#3cffd0] transition-colors">
              <div>
                <GraduationCap className="w-8 h-8 text-[#3cffd0] mb-4" />
                <h3 className="verge-label text-base text-white mb-2">{t('feat_copilot_title')}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{t('feat_copilot_desc')}</p>
              </div>
              <span className="text-[10px] text-gray-600 font-mono mt-6">Aligned to Grades 7-12</span>
            </div>
          </div>
        </div>
      </section>

      {/* Role Based Info Panels */}
      <section className="py-20 border-b border-[#2d2d2d]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="border border-[#2d2d2d] p-8 bg-[#181818] relative overflow-hidden group hover:border-[#5200ff] transition-all">
              <span className="verge-label text-[#3cffd0] block mb-4">Core Track</span>
              <h3 className="verge-display text-2xl font-black text-white mb-4">{t('role_student_title')}</h3>
              <p className="text-gray-400 text-sm leading-relaxed font-sans mb-6">{t('role_student_desc')}</p>
              <div className="absolute bottom-0 right-0 p-4 translate-x-4 translate-y-4 group-hover:translate-x-0 group-hover:translate-y-0 transition-transform opacity-10 group-hover:opacity-40">
                <MessageSquare className="w-16 h-16 text-[#3cffd0]" />
              </div>
            </div>

            <div className="border border-[#2d2d2d] p-8 bg-[#181818] relative overflow-hidden group hover:border-[#5200ff] transition-all">
              <span className="verge-label text-[#3cffd0] block mb-4">Educator Workspace</span>
              <h3 className="verge-display text-2xl font-black text-white mb-4">{t('role_teacher_title')}</h3>
              <p className="text-gray-400 text-sm leading-relaxed font-sans mb-6">{t('role_teacher_desc')}</p>
              <div className="absolute bottom-0 right-0 p-4 translate-x-4 translate-y-4 group-hover:translate-x-0 group-hover:translate-y-0 transition-transform opacity-10 group-hover:opacity-40">
                <Users className="w-16 h-16 text-[#3cffd0]" />
              </div>
            </div>

            <div className="border border-[#2d2d2d] p-8 bg-[#181818] relative overflow-hidden group hover:border-[#5200ff] transition-all">
              <span className="verge-label text-[#3cffd0] block mb-4">Family Circle</span>
              <h3 className="verge-display text-2xl font-black text-white mb-4">{t('role_parent_title')}</h3>
              <p className="text-gray-400 text-sm leading-relaxed font-sans mb-6">{t('role_parent_desc')}</p>
              <div className="absolute bottom-0 right-0 p-4 translate-x-4 translate-y-4 group-hover:translate-x-0 group-hover:translate-y-0 transition-transform opacity-10 group-hover:opacity-40">
                <Award className="w-16 h-16 text-[#3cffd0]" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Real-Time Stats Route Section */}
      <section id="stats" className="py-20 bg-[#1c1c1c] border-b border-[#2d2d2d] relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center mb-16">
            <h2 className="verge-display text-3xl sm:text-4xl text-white mb-2">{t('stats_title')}</h2>
            <div className="inline-flex items-center space-x-2 bg-[#3cffd0]/10 border border-[#3cffd0]/30 px-3 py-1 font-mono text-[10px] text-[#3cffd0]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#3cffd0] animate-ping" />
              <span>Real-Time platform counts</span>
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="border border-[#2d2d2d] bg-[#131313] p-6 text-center">
              <span className="verge-display text-3xl sm:text-5xl font-black text-white block mb-2">{stats.active_students.toLocaleString()}</span>
              <span className="verge-label text-gray-500">{t('stats_students')}</span>
            </div>

            <div className="border border-[#2d2d2d] bg-[#131313] p-6 text-center">
              <span className="verge-display text-3xl sm:text-5xl font-black text-white block mb-2">{stats.quizzes_completed.toLocaleString()}</span>
              <span className="verge-label text-gray-500">{t('stats_quizzes')}</span>
            </div>

            <div className="border border-[#2d2d2d] bg-[#131313] p-6 text-center">
              <span className="verge-display text-3xl sm:text-5xl font-black text-white block mb-2">{stats.lesson_plans_generated.toLocaleString()}</span>
              <span className="verge-label text-gray-500">{t('stats_lessons')}</span>
            </div>

            <div className="border border-[#2d2d2d] bg-[#131313] p-6 text-center">
              <span className="verge-display text-3xl sm:text-5xl font-black text-white block mb-2">{stats.knowledge_assets.toLocaleString()}</span>
              <span className="verge-label text-gray-500">{t('stats_assets')}</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
