import type { Request, Response } from "express";
import { AccessToken, type RoomConfiguration } from "livekit-server-sdk";

export async function handleToken(req: Request, res: Response): Promise<void> {
  const user = req.authUser!;

  const {
    room_name: roomName,
    participant_identity: participantIdentity,
    participant_name: participantName,
    participant_metadata: participantMetadata,
    participant_attributes: participantAttributes,
    room_config: roomConfig,
  } = req.body as {
    room_name?: string;
    participant_identity?: string;
    participant_name?: string;
    participant_metadata?: string;
    participant_attributes?: Record<string, string>;
    room_config?: RoomConfiguration;
  };

  const at = new AccessToken(
    process.env.LIVEKIT_API_KEY!,
    process.env.LIVEKIT_API_SECRET!,
    {
      identity: participantIdentity ?? user.login,
      name: participantName ?? user.name ?? user.login,
      metadata: participantMetadata,
      attributes: participantAttributes,
      ttl: "15m",
    },
  );

  at.addGrant({
    roomJoin: true,
    room: roomName ?? `room-${Date.now()}`,
    canPublish: true,
    canSubscribe: true,
  });

  if (roomConfig) {
    at.roomConfig = roomConfig;
  }

  const participantToken = await at.toJwt();

  res.status(201).json({
    server_url: process.env.LIVEKIT_URL,
    participant_token: participantToken,
  });
}
