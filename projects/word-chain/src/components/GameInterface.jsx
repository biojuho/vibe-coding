import React, { useState, useEffect, useRef } from 'react';
import { motion as Motion, AnimatePresence } from 'framer-motion';
import { Send, Terminal, Cpu } from 'lucide-react';
import { getRandomWord } from '../utils/dictionary';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import bgCyberpunk from '../assets/bg-cyberpunk.png';

const GameInterface = () => {
    const [history, setHistory] = useState([
        { text: "끝말잇기 시작!", sender: 'system' },
        { text: "단어를 입력하여 끝말잇기를 시작하세요!", sender: 'system' }
    ]);
    const [input, setInput] = useState('');
    const [turn, setTurn] = useState('player'); // player, com
    const [score, setScore] = useState(0);
    const [highScore, setHighScore] = useState(parseInt(localStorage.getItem('wordChainHighScore') || '0'));
    const [timeLeft, setTimeLeft] = useState(10);
    const [gameOver, setGameOver] = useState(false);
    const scrollRef = useRef(null);
    const timerRef = useRef(null);
    const highScoreRef = useRef(parseInt(localStorage.getItem('wordChainHighScore') || '0'));

    function handleGameOver(reason) {
        setGameOver(true);
        setHistory(prev => [...prev, { text: `❌ ${reason}`, sender: 'system' }]);
        clearInterval(timerRef.current);
    }

    const addScore = (delta) => {
        setScore(prevScore => {
            const nextScore = prevScore + delta;
            if (nextScore > highScoreRef.current) {
                highScoreRef.current = nextScore;
                setHighScore(nextScore);
                localStorage.setItem('wordChainHighScore', nextScore.toString());
            }
            return nextScore;
        });
    };

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [history]);

    // Timer Logic
    useEffect(() => {
        if (gameOver) return;

        timerRef.current = setInterval(() => {
            setTimeLeft(prev => {
                if (prev <= 1) {
                    clearInterval(timerRef.current);
                    setTimeout(() => handleGameOver("시간 초과! 패배했습니다."), 0);
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);

        return () => clearInterval(timerRef.current);
    }, [timeLeft, gameOver, turn]);

    const resetGame = () => {
        setHistory([
            { text: "끝말잇기 시작!", sender: 'system' },
            { text: "새 게임이 시작됐습니다! 단어를 입력하세요!", sender: 'system' }
        ]);
        setScore(0);
        setGameOver(false);
        setTurn('player');
        setTimeLeft(10);
        setInput('');
    };

    const handleSend = (e) => {
        e.preventDefault();
        if (!input.trim() || turn !== 'player' || gameOver) return;

        const word = input.trim();

        // Validation Logic
        const lastWord = history.filter(h => h.sender !== 'system').slice(-1)[0];
        if (lastWord && lastWord.text.slice(-1) !== word[0]) {
            setHistory(prev => [...prev, { text: `⚠️ '${lastWord.text.slice(-1)}'(으)로 시작해야 합니다`, sender: 'system' }]);
            // Penalty for wrong word? For now just warning.
            return;
        }

        // Already used word check (Optional but good)
        if (history.some(h => h.sender !== 'system' && h.text === word)) {
            setHistory(prev => [...prev, { text: `⚠️ 이미 사용된 단어입니다`, sender: 'system' }]);
            return;
        }

        // Success
        setHistory(prev => [...prev, { text: word, sender: 'player' }]);
        setInput('');
        addScore(10);
        setTurn('com');
        setTimeLeft(10); // Reset timer for AI

        // AI Turn Simulation
        setTimeout(() => {
            if (gameOver) return;

            const aiWord = getAIResponse(word);

            if (aiWord.includes('(GG)')) {
                handleGameOver("AI가 단어를 못 찾았습니다. 승리! 🎉");
                addScore(50); // Bonus for winning
            } else {
                setHistory(prev => [...prev, { text: aiWord, sender: 'com' }]);
                setTurn('player');
                setTimeLeft(10); // Reset timer for Player
            }
        }, 1200);
    };

    const getAIResponse = (lastWord) => {
        const char = lastWord.slice(-1);
        const found = getRandomWord(char);
        return found || `${char}... 단어를 모르겠어요 (GG)`;
    };

    return (
        <div 
            className="flex flex-col h-screen max-w-md mx-auto bg-cyber-bg border-x-2 border-cyber-pink/30 shadow-[0_0_50px_rgba(255,42,109,0.2)] relative bg-cover bg-center"
            style={{ backgroundImage: `url(${bgCyberpunk})` }}
        >
            {/* Header */}
            <header className="p-4 border-b-2 border-cyber-blue/50 bg-black/40 backdrop-blur flex justify-between items-center sticky top-0 z-10">
                <div className="flex flex-col">
                    <div className="flex items-center gap-2 text-cyber-blue animate-pulse">
                        <Terminal size={20} className="hidden sm:block" />
                        <img 
                            src="/src/assets/logo-neon.png" 
                            alt="WORD_CHAIN.EXE" 
                            className="h-6 sm:h-8 object-contain" 
                            onError={(e) => { e.target.style.display='none'; e.target.nextSibling.style.display='block'; }} 
                        />
                        <h1 className="font-bold text-xl tracking-tighter" style={{ display: 'none' }}>WORD_CHAIN.EXE</h1>
                    </div>
                </div>
                <div className="text-right space-y-1">
                    <Badge className="text-cyber-pink border-cyber-pink/30 bg-cyber-pink/10 font-mono text-sm">SCORE: {score.toString().padStart(4, '0')}</Badge>
                    <div className="text-xs text-cyber-blue/60">HI: {highScore}</div>
                </div>
            </header>

            {/* Timer Bar */}
            <div className="w-full h-1 bg-gray-800">
                <Motion.div
                    initial={{ width: "100%" }}
                    animate={{ width: `${(timeLeft / 10) * 100}%` }}
                    className={`h-full ${timeLeft < 3 ? 'bg-red-500' : 'bg-cyber-blue'}`}
                />
            </div>

            {/* Chat Area */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                <AnimatePresence>
                    {history.map((msg, idx) => (
                        <Motion.div
                            key={idx}
                            initial={{ opacity: 0, y: 10, scale: 0.9 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            className={`flex ${msg.sender === 'player' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div className={`
                                max-w-[80%] p-3 rounded-lg border 
                                ${msg.sender === 'player'
                                    ? 'bg-cyber-pink/10 border-cyber-pink text-cyber-pink rounded-tr-none'
                                    : msg.sender === 'system'
                                        ? 'bg-gray-800/50 border-gray-600 text-gray-400 text-sm'
                                        : 'bg-cyber-blue/10 border-cyber-blue text-cyber-blue rounded-tl-none'
                                }
                                backdrop-blur shadow-[0_0_15px_rgba(0,0,0,0.3)]
                            `}>
                                {msg.sender === 'com' && <Cpu size={14} className="mb-1 inline-block mr-2" />}
                                {msg.text}
                            </div>
                        </Motion.div>
                    ))}
                    {turn === 'com' && !gameOver && (
                        <Motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                            <div className="text-cyber-blue text-sm animate-pulse">AI is thinking...</div>
                        </Motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Game Over Modal */}
            <AnimatePresence>
                {gameOver && (
                    <Motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="absolute inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-6"
                    >
                        <Motion.div
                            initial={{ scale: 0.8, y: 20 }}
                            animate={{ scale: 1, y: 0 }}
                            className="max-w-sm w-full"
                        >
                            <Card className="text-center">
                                <CardHeader>
                                    <CardTitle>GAME OVER</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <p className="text-gray-300">{history[history.length - 1].text}</p>
                                    <div className="space-y-2">
                                        <div className="text-2xl font-mono text-white">SCORE: {score}</div>
                                        {score >= highScore && score > 0 && (
                                            <div className="text-cyber-yellow text-sm font-bold animate-pulse">🏆 NEW HIGH SCORE!</div>
                                        )}
                                    </div>
                                </CardContent>
                                <CardFooter className="justify-center">
                                    <Button
                                        onClick={resetGame}
                                        className="w-full"
                                        size="lg"
                                    >
                                        TRY AGAIN
                                    </Button>
                                </CardFooter>
                            </Card>
                        </Motion.div>
                    </Motion.div>
                )}
            </AnimatePresence>

            {/* Input Area */}
            <form onSubmit={handleSend} className="p-4 border-t-2 border-cyber-pink/50 bg-black/60 sticky bottom-0">
                <div className="relative">
                    <Input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        disabled={turn !== 'player' || gameOver}
                        placeholder={gameOver ? "게임 오버" : turn === 'player' ? `단어를 입력하세요.. (${timeLeft}s)` : "AI 생각중..."}
                        autoFocus
                    />
                    <Button
                        type="submit"
                        disabled={!input.trim() || turn !== 'player' || gameOver}
                        size="icon"
                        className="absolute right-2 top-1/2 -translate-y-1/2"
                    >
                        <Send size={18} />
                    </Button>
                </div>
            </form>
        </div>
    );
};

export default GameInterface;



