import { AbsoluteFill } from "remotion";
import {
  ImessageChatFlow,
  type ImessageMessage,
} from "@/components/remocn/imessage-chat-flow";

// A new content format (2026-09-21, per request): a scripted iMessage-style
// exchange instead of a single caption -- the jar mechanic as a punchline
// two people are actually texting about, not a caption describing it.
// accentColor uses the brand coral so the outgoing bubbles read as "ours"
// without breaking the iMessage-recognizable gray/colored convention.
export const JAR_BANTER_MESSAGES: ImessageMessage[] = [
  { from: "them", text: "did you seriously add \"left on read for 4 hours\" to the jar" },
  { from: "me", text: "you were online. i saw the little green dot 👀" },
  { from: "them", text: "that was for work" },
  { from: "me", text: "the jar doesn't know that ❤️", reaction: "😭" },
];

export const JarBanter: React.FC<{ messages: ImessageMessage[] }> = ({
  messages,
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#ffffff" }}>
      <ImessageChatFlow
        messages={messages}
        contact={{ name: "him" }}
        accentColor="#EA4330"
      />
    </AbsoluteFill>
  );
};
