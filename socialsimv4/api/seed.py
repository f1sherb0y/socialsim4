import asyncio
import json

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from socialsimv4.api.config import DATABASE_URL
from socialsimv4.api.database import Base, SimulationTemplate

# --- Template Definitions ---

# 1. Simple Chat Scene Template
simple_chat_template = {
    "name": "Simple Chat Room",
    "description": "A basic chat room where agents can interact with each other.",
    "template_json": json.dumps(
        {
            "agents": [
                {
                    "name": "Alice",
                    "user_profile": "Alice is a friendly and outgoing software engineer who loves to talk about technology and hiking.",
                    "style": "casual and enthusiastic",
                    "initial_instruction": "You are Alice. Greet everyone and start a conversation.",
                    "role_prompt": "You are a participant in a chat room.",
                    "action_space": ["send_message"],
                },
                {
                    "name": "Bob",
                    "user_profile": "Bob is a quiet and reserved artist who prefers to listen more than talk.",
                    "style": "thoughtful and concise",
                    "initial_instruction": "You are Bob. Respond to others if you have something interesting to say.",
                    "role_prompt": "You are a participant in a chat room.",
                    "action_space": ["send_message"],
                },
            ],
            "scenario": {
                "type": "simple_chat",
                "name": "Simple Chat",
                "initial_event": "The chat room is now open.",
            },
        }
    ),
    "is_public": True,
}

# 2. Map Scene Template
map_scene_template = {
    "name": "Virtual Village",
    "description": "A village with various locations where agents can move, gather resources, and interact.",
    "template_json": json.dumps(
        {
            "agents": [
                {
                    "name": "Farmer John",
                    "user_profile": "John is a hardworking farmer who has lived in this village his whole life. He is concerned with the harvest and the well-being of his animals.",
                    "style": "practical and a bit rustic",
                    "initial_instruction": "You are Farmer John. It's a new day, and you need to check on your crops.",
                    "role_prompt": "You are a resident of a small village.",
                    "action_space": [
                        "move_to_location",
                        "gather_resource",
                        "look_around",
                        "rest",
                        "send_message",
                    ],
                },
                {
                    "name": "Merchant Sarah",
                    "user_profile": "Sarah is a shrewd merchant who travels between villages. She is always looking for opportunities to trade and make a profit.",
                    "style": "persuasive and business-like",
                    "initial_instruction": "You are Merchant Sarah. You have just arrived in the village and are looking for goods to trade.",
                    "role_prompt": "You are a traveling merchant.",
                    "action_space": [
                        "move_to_location",
                        "gather_resource",
                        "look_around",
                        "rest",
                        "send_message",
                    ],
                },
            ],
            "scenario": {
                "type": "map",
                "name": "Virtual Village",
                "initial_event": "A new day has begun in the village.",
            },
        }
    ),
    "is_public": True,
}

# 3. Council Scene Template
council_scene_template = {
    "name": "Town Council Meeting",
    "description": "A formal meeting where agents discuss and vote on important issues.",
    "template_json": json.dumps(
        {
            "agents": [
                {
                    "name": "Mayor Adams",
                    "user_profile": "Mayor Adams is the pragmatic leader of the town, focused on maintaining order and balancing the budget.",
                    "style": "formal and diplomatic",
                    "initial_instruction": "You are Mayor Adams. You must lead the council meeting and ensure a decision is made on the new proposal.",
                    "role_prompt": "You are the mayor and chair of the town council.",
                    "action_space": ["send_message", "cast_vote"],
                },
                {
                    "name": "Councilor Brown",
                    "user_profile": "Councilor Brown is a passionate environmentalist who advocates for green policies.",
                    "style": "passionate and sometimes confrontational",
                    "initial_instruction": "You are Councilor Brown. You must argue against the new factory proposal.",
                    "role_prompt": "You are a member of the town council.",
                    "action_space": ["send_message", "cast_vote"],
                },
                {
                    "name": "Councilor Green",
                    "user_profile": "Councilor Green is a business owner focused on economic growth and job creation.",
                    "style": "persuasive and data-driven",
                    "initial_instruction": "You are Councilor Green. You must argue in favor of the new factory proposal.",
                    "role_prompt": "You are a member of the town council.",
                    "action_space": ["send_message", "cast_vote"],
                },
            ],
            "scenario": {
                "type": "council",
                "name": "Town Council Meeting",
                "initial_event": "The town council meeting has been called to order to discuss the proposal for a new factory.",
            },
        }
    ),
    "is_public": True,
}

templates_to_add = [simple_chat_template, map_scene_template, council_scene_template]


async def seed_database():
    engine = create_async_engine(DATABASE_URL, echo=True)
    AsyncSessionLocal = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        for template_data in templates_to_add:
            # Check if a template with the same name already exists
            result = await db.execute(
                SimulationTemplate.__table__.select().where(
                    SimulationTemplate.name == template_data["name"]
                )
            )
            if result.first() is None:
                db_template = SimulationTemplate(**template_data)
                db.add(db_template)
                print(f"Adding template: {template_data['name']}")
            else:
                print(f"Template '{template_data['name']}' already exists. Skipping.")

        await db.commit()
    print("Database seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed_database())
