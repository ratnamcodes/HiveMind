import { NextResponse } from "next/server";
import { addMessage, getMessages, markRead } from "@/lib/mock/data";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ channel_id: string }> },
) {
  const { channel_id } = await params;
  markRead(channel_id);
  return NextResponse.json(getMessages(channel_id));
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ channel_id: string }> },
) {
  const { channel_id } = await params;
  const body = (await req.json().catch(() => ({}))) as { text?: string };
  const text = (body.text ?? "").trim();
  if (!text) {
    return NextResponse.json({ error: "text is required" }, { status: 400 });
  }
  const message = addMessage(channel_id, text);
  return NextResponse.json(message, { status: 201 });
}
