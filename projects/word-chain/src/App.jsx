import GameInterface from './components/GameInterface'

function App() {
  return (
    <div className="games-screen w-full min-h-screen bg-[url('https://images.unsplash.com/photo-1550751827-4bd374c3f58b')] bg-cover bg-center bg-no-repeat bg-fixed">
      <div className="w-full h-full min-h-screen bg-black/80 backdrop-blur-sm">
        <GameInterface />
      </div>
    </div>
  )
}

export default App
