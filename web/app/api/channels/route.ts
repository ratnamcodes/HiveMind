import { NextResponse } from "next/server";
import { getChannels } from "@/lib/mock/data";

export async function GET() {
  return NextResponse.json(getChannels());
}
