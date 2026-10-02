import { AbsoluteFill } from "remotion";

// Text-bubble reels (batch 3, 2026-10-02): a plain iOS iMessage screenshot
// (light mode) centred on black, the way real screenshot reels look --
// black bars above/below, nothing branded, no animation. Static for the whole
// clip; the user adds trending audio at upload. Sizes are iOS points x3
// (1080px wide = 360pt). Post-render, the mp4 gets a light soften pass in
// ffmpeg so it reads as a re-shared screenshot rather than a crisp design.
export type ChatMessage = { from: "me" | "them"; text: string };

export type ChatScreenshotProps = {
  contact: string;
  initials: string;
  statusTime: string; // status bar clock, e.g. "6:43"
  timestamp: string; // e.g. "Today 6:42 PM"
  readAt: string; // e.g. "Read 6:43 PM"
  messages: ChatMessage[];
  screenHeight: number; // px of the screenshot; rest is black bars
};

const FONT = '-apple-system, "SF Pro Text", "Helvetica Neue", Arial, sans-serif';
const BLUE = "#0A84FF";
const GREY_BUBBLE = "#E9E9EB";
const GREY_TEXT = "#8E8E93";

const StatusBar: React.FC<{ time: string }> = ({ time }) => (
  <div style={{ height: 150, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 84px 0 96px", fontFamily: FONT }}>
    <span style={{ fontSize: 51, fontWeight: 600, color: "#000" }}>{time}</span>
    <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
      <svg width="54" height="36" viewBox="0 0 18 12">
        {[0, 1, 2, 3].map((i) => (
          <rect key={i} x={i * 4.8} y={9 - i * 3} width="3.2" height={3 + i * 3} rx="0.8" fill="#000" />
        ))}
      </svg>
      <svg width="48" height="36" viewBox="0 0 16 12">
        <path d="M8 11.2 5.6 8.8a3.4 3.4 0 0 1 4.8 0z M3.4 6.6a6.5 6.5 0 0 1 9.2 0l-1.4 1.4a4.5 4.5 0 0 0-6.4 0z M1.2 4.4a9.6 9.6 0 0 1 13.6 0l-1.4 1.4a7.6 7.6 0 0 0-10.8 0z" fill="#000" />
      </svg>
      <svg width="81" height="39" viewBox="0 0 27 13">
        <rect x="0.5" y="0.5" width="23" height="12" rx="3.5" fill="none" stroke="#000" strokeOpacity="0.4" />
        <rect x="2" y="2" width="16" height="9" rx="2" fill="#000" />
        <rect x="24.5" y="4.5" width="1.6" height="4" rx="0.8" fill="#000" fillOpacity="0.4" />
      </svg>
    </div>
  </div>
);

const Header: React.FC<{ contact: string; initials: string }> = ({ contact, initials }) => (
  <div style={{ position: "relative", height: 270, flexShrink: 0, borderBottom: "1px solid #D8D8DC", background: "#F7F7F7", fontFamily: FONT }}>
    <svg style={{ position: "absolute", left: 36, top: 60 }} width="42" height="66" viewBox="0 0 14 22">
      <path d="M12 2 3 11l9 9" fill="none" stroke={BLUE} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
    <div style={{ position: "absolute", left: 0, right: 0, top: 18, display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div style={{ width: 150, height: 150, borderRadius: 75, background: "linear-gradient(#A5ABB8, #858994)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 66, fontWeight: 500 }}>
        {initials}
      </div>
      <div style={{ marginTop: 12, fontSize: 36, color: "#000", display: "flex", alignItems: "center", gap: 6 }}>
        {contact}
        <span style={{ color: GREY_TEXT, fontSize: 30 }}>›</span>
      </div>
    </div>
  </div>
);

const Tail: React.FC<{ side: "left" | "right"; color: string }> = ({ side, color }) => (
  <svg
    width="36"
    height="45"
    viewBox="0 0 12 15"
    style={{ position: "absolute", bottom: 0, [side]: -12, transform: side === "left" ? "scaleX(-1)" : undefined }}
  >
    <path d="M0 0v9c0 3.5 3 6 9 6h3c-4-1.2-6-4.5-6-9V0z" fill={color} />
  </svg>
);

const Bubble: React.FC<{ msg: ChatMessage; tail: boolean }> = ({ msg, tail }) => {
  const mine = msg.from === "me";
  const bg = mine ? BLUE : GREY_BUBBLE;
  return (
    <div style={{ display: "flex", justifyContent: mine ? "flex-end" : "flex-start", padding: "0 42px" }}>
      <div
        style={{
          position: "relative",
          maxWidth: 740,
          background: bg,
          color: mine ? "#fff" : "#000",
          borderRadius: 54,
          padding: "21px 39px",
          fontSize: 51,
          lineHeight: 1.25,
          fontFamily: FONT,
          letterSpacing: -0.4,
        }}
      >
        {msg.text}
        {tail ? <Tail side={mine ? "right" : "left"} color={bg} /> : null}
      </div>
    </div>
  );
};

const InputBar: React.FC = () => (
  <div style={{ height: 170, flexShrink: 0, display: "flex", alignItems: "flex-start", gap: 24, padding: "18px 36px 0", fontFamily: FONT }}>
    <div style={{ width: 96, height: 96, borderRadius: 48, background: "#E9E9EB", display: "flex", alignItems: "center", justifyContent: "center", color: "#7C7C80", fontSize: 66, fontWeight: 300 }}>+</div>
    <div style={{ flex: 1, height: 96, borderRadius: 48, border: "2px solid #D1D1D6", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 36px", color: "#C4C4C7", fontSize: 48 }}>
      iMessage
      <svg width="30" height="48" viewBox="0 0 10 16">
        <rect x="2.5" y="0.5" width="5" height="9.5" rx="2.5" fill="#C4C4C7" />
        <path d="M0.8 7.5a4.2 4.2 0 0 0 8.4 0M5 11.8V15" fill="none" stroke="#C4C4C7" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    </div>
  </div>
);

export const ChatScreenshot: React.FC<ChatScreenshotProps> = ({ contact, initials, statusTime, timestamp, readAt, messages, screenHeight }) => {
  const lastMine = messages.map((m) => m.from).lastIndexOf("me");
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", justifyContent: "center" }}>
      <div style={{ height: screenHeight, background: "#fff", display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <StatusBar time={statusTime} />
        <Header contact={contact} initials={initials} />
        <div style={{ flex: 1, minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column", justifyContent: "flex-end", paddingBottom: 24 }}>
          <div style={{ textAlign: "center", fontFamily: FONT, fontSize: 33, color: GREY_TEXT, marginBottom: 30 }}>
            <div>iMessage</div>
            <div>
              <b style={{ fontWeight: 600 }}>{timestamp.split(" ")[0]}</b> {timestamp.split(" ").slice(1).join(" ")}
            </div>
          </div>
          {messages.map((m, i) => {
            const next = messages[i + 1];
            const lastInGroup = !next || next.from !== m.from;
            return (
              <div key={i} style={{ marginBottom: lastInGroup ? 24 : 6 }}>
                <Bubble msg={m} tail={lastInGroup} />
                {i === lastMine ? (
                  <div style={{ textAlign: "right", padding: "9px 48px 0", fontFamily: FONT, fontSize: 33, color: GREY_TEXT }}>
                    <b style={{ fontWeight: 600 }}>Read</b> {readAt.replace(/^Read /, "")}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
        <InputBar />
      </div>
    </AbsoluteFill>
  );
};
