#!/usr/bin/env python3
"""
Create test data for comprehensive location tracking system testing.
This creates guides, tourists, and trip assignments for realistic testing.
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Trip, AsyncSessionLocal
import hashlib

async def create_comprehensive_test_data():
    """Create comprehensive test data for location tracking testing"""
    async with AsyncSessionLocal() as db:
        try:
            print("🔧 Creating comprehensive test data for location tracking tests...")
            
            # Create test guide
            test_guide_email = "testguide@demo.com"
            result = await db.execute(select(User).filter(User.email == test_guide_email))
            test_guide = result.scalar_one_or_none()
            
            if not test_guide:
                test_guide = User(
                    email=test_guide_email,
                    hashed_password=User.get_password_hash("testguide123"),
                    full_name="Test Guide",
                    contact_number="+1234567893",
                    age=30,
                    gender="M",
                    role="guide"
                )
                db.add(test_guide)
                await db.commit()
                await db.refresh(test_guide)
                print(f"✅ Created test guide: {test_guide_email}")
            else:
                print(f"✅ Test guide already exists: {test_guide_email}")
            
            # Create test tourist
            test_tourist_email = "testtourist@demo.com" 
            result = await db.execute(select(User).filter(User.email == test_tourist_email))
            test_tourist = result.scalar_one_or_none()
            
            if not test_tourist:
                test_tourist = User(
                    email=test_tourist_email,
                    hashed_password=User.get_password_hash("testtourist123"),
                    full_name="Test Tourist",
                    contact_number="+1234567894",
                    age=25,
                    gender="F",
                    role="tourist"
                )
                db.add(test_tourist)
                await db.commit()
                await db.refresh(test_tourist)
                print(f"✅ Created test tourist: {test_tourist_email}")
            else:
                print(f"✅ Test tourist already exists: {test_tourist_email}")
            
            # Create test trip with guide assignment
            result = await db.execute(
                select(Trip).filter(
                    Trip.user_id == test_tourist.id,
                    Trip.is_active == True
                )
            )
            existing_trip = result.scalar_one_or_none()
            
            if not existing_trip:
                # Generate blockchain ID
                blockchain_data = f"{test_tourist.full_name}_{test_tourist.email}_trip"
                blockchain_id = hashlib.sha256(blockchain_data.encode()).hexdigest()[:16]
                
                test_trip = Trip(
                    user_id=test_tourist.id,
                    guide_id=test_guide.id,  # Assign guide to tourist
                    blockchain_id=blockchain_id,
                    starting_location="New Delhi Railway Station",
                    tourist_destination_id=1,  # Taj Mahal
                    last_lat=28.6139,  # Delhi coordinates
                    last_lon=77.2090,
                    status="Safe",
                    hotels='[{"name": "Test Hotel", "address": "Test Address"}]',
                    mode_of_travel="train",
                    is_active=True
                )
                db.add(test_trip)
                await db.commit()
                await db.refresh(test_trip)
                print(f"✅ Created test trip with guide assignment: Trip ID {test_trip.id}")
            else:
                # Update existing trip to have guide assignment
                existing_trip.guide_id = test_guide.id
                await db.commit()
                print(f"✅ Updated existing trip with guide assignment: Trip ID {existing_trip.id}")
            
            # Create additional test tourists for comprehensive testing
            additional_tourists = [
                ("tourist2@demo.com", "Test Tourist 2", "+1234567895", 28, "M"),
                ("tourist3@demo.com", "Test Tourist 3", "+1234567896", 22, "F"),
            ]
            
            for email, name, contact, age, gender in additional_tourists:
                result = await db.execute(select(User).filter(User.email == email))
                existing_user = result.scalar_one_or_none()
                
                if not existing_user:
                    new_tourist = User(
                        email=email,
                        hashed_password=User.get_password_hash("tourist123"),
                        full_name=name,
                        contact_number=contact,
                        age=age,
                        gender=gender,
                        role="tourist"
                    )
                    db.add(new_tourist)
                    await db.commit()
                    await db.refresh(new_tourist)
                    
                    # Create trip for this tourist (some with guide, some without)
                    blockchain_data = f"{name}_{email}_trip"
                    blockchain_id = hashlib.sha256(blockchain_data.encode()).hexdigest()[:16]
                    
                    # Assign guide to tourist2 only
                    guide_assignment = test_guide.id if "tourist2" in email else None
                    
                    new_trip = Trip(
                        user_id=new_tourist.id,
                        guide_id=guide_assignment,
                        blockchain_id=blockchain_id,
                        starting_location="Mumbai Central Station",
                        tourist_destination_id=2,  # Red Fort
                        last_lat=28.6562,  # Red Fort coordinates  
                        last_lon=77.2410,
                        status="Safe",
                        hotels='[{"name": "Mumbai Hotel", "address": "Mumbai Address"}]',
                        mode_of_travel="flight",
                        is_active=True
                    )
                    db.add(new_trip)
                    print(f"✅ Created additional tourist and trip: {name}")
            
            await db.commit()
            
            print("\n🎯 Test Data Summary:")
            print(f"   • Test Guide: {test_guide_email} / testguide123")
            print(f"   • Test Tourists: {test_tourist_email} / testtourist123")
            print(f"   • Additional Tourists: tourist2@demo.com, tourist3@demo.com")
            print(f"   • Active Trips with Guide Assignments Created")
            print(f"   • Ready for comprehensive location tracking testing!")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating test data: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            return False

async def main():
    success = await create_comprehensive_test_data()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)